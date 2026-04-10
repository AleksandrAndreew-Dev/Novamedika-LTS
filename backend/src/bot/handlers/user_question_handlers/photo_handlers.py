"""Обработчики фото рецепта: уточнение, отправка фото, загрузка."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.qa_models import User, Question, Answer, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.services.dialog_service import DialogService
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("quick_clarify_"))
async def quick_clarify_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Быстрое уточнение через кнопку в сообщении с ответом"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    try:
        question_uuid = callback.data.replace("quick_clarify_", "")

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if question.user_id != user.uuid:
            await callback.answer("❌ Этот вопрос не принадлежит вам", show_alert=True)
            return

        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        if not last_answer:
            await callback.answer("❌ На этот вопрос еще нет ответа", show_alert=True)
            return

        await state.update_data(clarify_question_id=question_uuid)
        await state.set_state(UserQAStates.waiting_for_clarification)

        photo_requested = question.context_data and question.context_data.get(
            "photo_requested", False
        )

        message_text = f"💬 <b>Уточнение к вопросу:</b>\n\n"
        message_text += f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"

        if last_answer:
            message_text += f"💬 <b>Полученный ответ:</b>\n{last_answer.text}\n\n"

        if photo_requested:
            message_text += (
                "📸 <b>Фармацевт запросил фото рецепта для этого вопроса.</b>\n"
            )
            message_text += "Вы можете отправить его после уточнения.\n\n"

        message_text += "✍️ <b>Напишите ваше уточнение ниже:</b>\n"
        message_text += "(или /cancel для отмены)"

        await callback.message.answer(message_text, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in quick_clarify_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании уточнения", show_alert=True)


@router.callback_query(F.data.startswith("send_prescription_photo_"))
async def send_prescription_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Обработка нажатия кнопки отправки фото рецепта"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("send_prescription_photo_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer(
                "❌ Вопрос не найден или не принадлежит вам", show_alert=True
            )
            return

        if question.status == "completed":
            await callback.answer(
                "❌ Этот диалог уже завершён. Нельзя отправлять фото.",
                show_alert=True,
            )
            return

        pharmacist_id = None

        if question.context_data and "photo_requested_by" in question.context_data:
            pharmacist_id = question.context_data["photo_requested_by"].get(
                "pharmacist_id"
            )
        elif question.taken_by:
            pharmacist_id = str(question.taken_by)

        if not pharmacist_id:
            await callback.answer(
                "❌ Не найден фармацевт для отправки фото", show_alert=True
            )
            return

        pharmacist_result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        requested_pharmacist = pharmacist_result.scalar_one_or_none()

        if not requested_pharmacist or not requested_pharmacist.user:
            await callback.answer("❌ Фармацевт не найден", show_alert=True)
            return

        await state.update_data(
            prescription_photo_question_id=question_uuid,
            prescription_photo_pharmacist_id=str(requested_pharmacist.uuid),
            prescription_photo_message_id=callback.message.message_id,
        )
        await state.set_state(UserQAStates.waiting_for_prescription_photo)

        await callback.message.answer(
            "📸 <b>Отправка фото рецепта</b>\n\n"
            "Пожалуйста, отправьте фото рецепта одним из способов:\n\n"
            "1. <b>Как фото</b> - просто прикрепите фото к сообщению\n"
            "2. <b>Как документ</b> - если нужно сохранить качество\n\n"
            f"💡 <b>Фото будет отправлено фармацевту:</b>\n"
            f"👨‍⚕️ {requested_pharmacist.pharmacy_info.get('first_name', '')} "
            f"{requested_pharmacist.pharmacy_info.get('last_name', '')}\n\n"
            "💡 <b>Рекомендации:</b>\n"
            "• Убедитесь, что все надписи читаемы\n"
            "• Хорошее освещение\n"
            "• Весь рецепт в кадре\n\n"
            "Вы можете отправить несколько фото.\n"
            "Когда закончите, нажмите /done\n"
            "Для отмены: /cancel",
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in send_prescription_photo_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(UserQAStates.waiting_for_prescription_photo, F.photo)
async def process_prescription_photo(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка отправленного фото рецепта — сохраняет в буфер"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")

        if not question_uuid or not pharmacist_id:
            await message.answer("❌ Не удалось найти вопрос или фармацевта")
            await state.clear()
            return

        # Добавляем фото в буфер состояния
        photo_file_ids = state_data.get("photo_file_ids", [])
        photo = message.photo[-1]
        photo_file_ids.append(photo.file_id)
        await state.update_data(photo_file_ids=photo_file_ids)

        # Сохраняем в историю диалога
        await DialogService.add_message(
            db=db,
            question_id=question_uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="photo",
            file_id=photo.file_id,
            caption=message.caption,
        )
        await db.commit()

        count = len(photo_file_ids)

        if count == 1:
            # Первое фото — показываем его с инструкцией
            await message.answer_photo(
                photo=photo.file_id,
                caption=(
                    f"📸 <b>Фото 1 сохранено</b>\n\n"
                    f"Все фото будут отправлены фармацевту <b>одним альбомом</b>.\n\n"
                    f"👇 Продолжайте отправлять фото или выберите действие:"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📸 Отправить ещё фото",
                                callback_data=f"send_prescription_photo_{question_uuid}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить и отправить",
                                callback_data=f"finish_photo_upload_{question_uuid}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"cancel_photo_upload_{question_uuid}",
                            ),
                        ],
                    ]
                ),
            )
        else:
            # Последующие фото — тихое подтверждение без лишних сообщений
            await message.answer(
                f"✅ Фото {count} добавлено в альбом. Отправьте ещё или нажмите кнопку ниже.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить и отправить",
                                callback_data=f"finish_photo_upload_{question_uuid}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"cancel_photo_upload_{question_uuid}",
                            ),
                        ],
                    ]
                ),
            )

    except Exception as e:
        logger.error(f"Error processing prescription photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при сохранении фото")


@router.message(UserQAStates.waiting_for_prescription_photo, F.document)
async def process_prescription_document(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка документа (фото рецепта как документ)"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")

        if not question_uuid or not pharmacist_id:
            await message.answer("❌ Не удалось найти вопрос или фармацевта")
            await state.clear()
            return

        document = message.document
        if not document.mime_type.startswith("image/"):
            await message.answer("❌ Пожалуйста, отправьте изображение (фото)")
            return

        # Добавляем в буфер
        photo_file_ids = state_data.get("photo_file_ids", [])
        photo_file_ids.append(document.file_id)
        await state.update_data(photo_file_ids=photo_file_ids)

        await DialogService.add_message(
            db=db,
            question_id=question_uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="photo",
            file_id=document.file_id,
            caption=message.caption,
        )
        await db.commit()

        count = len(photo_file_ids)

        if count == 1:
            await message.answer(
                f"📸 <b>Фото 1 сохранено</b>\n\n"
                f"Все фото будут отправлены фармацевту <b>одним альбомом</b>.\n\n"
                f"👇 Продолжайте отправлять фото или выберите действие:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📸 Отправить ещё фото",
                                callback_data=f"send_prescription_photo_{question_uuid}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить и отправить",
                                callback_data=f"finish_photo_upload_{question_uuid}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"cancel_photo_upload_{question_uuid}",
                            ),
                        ],
                    ]
                ),
            )
        else:
            await message.answer(
                f"✅ Фото {count} добавлено в альбом. Отправьте ещё или нажмите кнопку ниже.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить и отправить",
                                callback_data=f"finish_photo_upload_{question_uuid}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"cancel_photo_upload_{question_uuid}",
                            ),
                        ],
                    ]
                ),
            )

    except Exception as e:
        logger.error(f"Error processing prescription document: {e}", exc_info=True)
        await message.answer("❌ Ошибка при сохранении фото")


@router.message(Command("done"), UserQAStates.waiting_for_prescription_photo)
@router.callback_query(F.data.startswith("finish_photo_upload_"))
async def finish_photo_upload(
    message_or_callback, state: FSMContext, db: AsyncSession, user: User
):
    """Завершение загрузки фото рецепта — отправка альбомом фармацевту"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")
        original_message_id = state_data.get("prescription_photo_message_id")
        photo_file_ids = state_data.get("photo_file_ids", [])

        if not question_uuid or not pharmacist_id:
            await _send_finish_response(
                message_or_callback, state, "❌ Не удалось найти вопрос или фармацевта"
            )
            return

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        if pharmacist and pharmacist.user and photo_file_ids:
            # Сначала показываем пользователю превью альбома
            media_group = [InputMediaPhoto(media=file_id) for file_id in photo_file_ids]

            preview_caption = (
                f"📸 <b>Альбом: {len(photo_file_ids)} фото</b>\n\n"
                f"Всё верно? Нажмите «✅ Отправить фармацевту»"
            )
            media_group[0].caption = preview_caption
            media_group[0].parse_mode = "HTML"

            await message_or_callback.bot.send_media_group(
                chat_id=message_or_callback.chat.id,
                media=media_group,
            )

            confirm_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Отправить фармацевту",
                            callback_data=f"confirm_send_photos_{question_uuid}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Отменить",
                            callback_data=f"cancel_photo_upload_{question_uuid}",
                        )
                    ],
                ]
            )

            await message_or_callback.bot.send_message(
                chat_id=message_or_callback.chat.id,
                text="👆 Это ваш альбом. Проверьте и подтвердите отправку.",
                reply_markup=confirm_keyboard,
            )
            return  # Ждём подтверждения

        await state.clear()

        if original_message_id:
            try:
                await message_or_callback.bot.edit_message_reply_markup(
                    chat_id=message_or_callback.chat.id,
                    message_id=original_message_id,
                    reply_markup=None,
                )
            except Exception:
                pass

        photo_count = len(photo_file_ids)
        await _send_finish_response(
            message_or_callback,
            state,
            f"✅ <b>Загрузка фото завершена</b> ({photo_count} шт.)\n\n"
            "Фармацевт получит фото и ответит вам.",
        )

    except Exception as e:
        logger.error(f"Error in finish_photo_upload: {e}", exc_info=True)
        await state.clear()
        await _send_finish_response(
            message_or_callback, state, "❌ Ошибка при завершении загрузки"
        )


@router.callback_query(F.data.startswith("confirm_send_photos_"))
async def confirm_send_photos_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
):
    """Отправка альбома фармацевту после подтверждения пользователем"""
    try:
        state_data = await state.get_data()
        question_uuid = callback.data.replace("confirm_send_photos_", "")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")
        photo_file_ids = state_data.get("photo_file_ids", [])

        if not pharmacist_id or not photo_file_ids:
            await callback.answer("❌ Ошибка: нет фото для отправки", show_alert=True)
            return

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        if pharmacist and pharmacist.user:
            media_group = [InputMediaPhoto(media=file_id) for file_id in photo_file_ids]

            history_text, _ = await DialogService.format_dialog_history_for_display(
                question_uuid, db
            )

            caption = (
                f"📸 <b>Получено фото рецепта ({len(photo_file_ids)} шт.)</b>\n\n"
                f"👤 <b>От пользователя:</b> {user_name}\n"
                f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{history_text}"
            )

            pharmacist_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💬 Ответить пользователю",
                            callback_data=f"answer_{question_uuid}",
                        ),
                        InlineKeyboardButton(
                            text="📸 Запросить еще фото",
                            callback_data=f"request_more_photos_{question_uuid}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ Завершить консультацию",
                            callback_data=f"end_dialog_{question_uuid}",
                        )
                    ],
                ]
            )

            try:
                media_group[0].caption = caption
                media_group[0].parse_mode = "HTML"

                await callback.bot.send_media_group(
                    chat_id=pharmacist.user.telegram_id,
                    media=media_group,
                )
                await callback.bot.send_message(
                    chat_id=pharmacist.user.telegram_id,
                    text=f"👆 Фото от {user_name}",
                    reply_markup=pharmacist_keyboard,
                )
            except TelegramBadRequest as e:
                logger.error(f"Error sending media group: {e}")
                for file_id in photo_file_ids:
                    await callback.bot.send_photo(
                        chat_id=pharmacist.user.telegram_id,
                        photo=file_id,
                        caption=caption if file_id == photo_file_ids[0] else None,
                        parse_mode="HTML" if file_id == photo_file_ids[0] else None,
                        reply_markup=(
                            pharmacist_keyboard
                            if file_id == photo_file_ids[0]
                            else None
                        ),
                    )

        await state.clear()

        await callback.message.answer(
            f"✅ <b>Альбом отправлен фармацевту!</b> ({len(photo_file_ids)} фото)\n\n"
            f"Фармацевт получит фото и ответит вам.",
            parse_mode="HTML",
        )
        await callback.answer("Фото отправлены")

    except Exception as e:
        logger.error(f"Error in confirm_send_photos_callback: {e}", exc_info=True)
        await state.clear()
        await callback.answer("❌ Ошибка при отправке", show_alert=True)


async def _send_finish_response(msg, state, text):
    """Отправить ответ пользователю в зависимости от типа сообщения."""
    if hasattr(msg, "answer"):
        await msg.answer(text, parse_mode="HTML")
    else:
        await msg.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("cancel_photo_upload_"))
async def cancel_photo_upload_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
):
    """Отмена загрузки фото — удаляет все сохранённые фото из истории"""
    try:
        state_data = await state.get_data()
        question_uuid = callback.data.replace("cancel_photo_upload_", "")
        photo_file_ids = state_data.get("photo_file_ids", [])

        # Удаляем сохранённые фото из истории
        if photo_file_ids:
            await DialogService.remove_photos_from_dialog(
                question_uuid, db, sender_type="user"
            )
            await db.commit()

        await state.clear()

        await callback.message.answer(
            f"❌ <b>Загрузка фото отменена</b>\n\n"
            f"Удалено фото: <b>{len(photo_file_ids)}</b>\n\n"
            f"Вы можете повторно отправить фото, нажав «📸 Отправить фото» в диалоге.",
            parse_mode="HTML",
        )
        await callback.answer("Загрузка отменена")

    except Exception as e:
        logger.error(f"Error in cancel_photo_upload_callback: {e}", exc_info=True)
        await state.clear()
        await callback.answer("Ошибка при отмене", show_alert=True)
