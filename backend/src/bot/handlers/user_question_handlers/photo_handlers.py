"""Обработчики фото рецепта: уточнение, отправка фото, загрузка."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

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
    """Обработка отправленного фото рецепта"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")

        if not question_uuid or not pharmacist_id:
            await message.answer("❌ Не удалось найти вопрос или фармацевта")
            await state.clear()
            return

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            await message.answer("❌ Фармацевт не найден")
            await state.clear()
            return

        question_result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = question_result.scalar_one_or_none()

        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        photo = message.photo[-1]

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

        history_text, _ = await DialogService.format_dialog_history_for_display(
            question_uuid, db
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

        await message.bot.send_photo(
            chat_id=pharmacist.user.telegram_id,
            photo=photo.file_id,
            caption=(
                f"📸 <b>Получено фото рецепта</b>\n\n"
                f"👤 <b>От пользователя:</b> {user_name}\n"
                f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{history_text}"
            ),
            parse_mode="HTML",
            reply_markup=pharmacist_keyboard,
        )

        await message.answer(
            f"✅ Фото рецепта отправлено фармацевту!\n\n"
            f"📸 <b>Фото добавлено в историю диалога.</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💬 Ответить",
                            callback_data=f"continue_dialog_{question_uuid}",
                        ),
                        InlineKeyboardButton(
                            text="✅ Завершить консультацию",
                            callback_data=f"end_dialog_{question_uuid}",
                        ),
                    ]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Error processing prescription photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке фото")


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

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            await message.answer("❌ Фармацевт не найден")
            await state.clear()
            return

        question_result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = question_result.scalar_one_or_none()

        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        pharmacist_name = "Фармацевт"
        if pharmacist.pharmacy_info:
            first_name = pharmacist.pharmacy_info.get("first_name", "")
            last_name = pharmacist.pharmacy_info.get("last_name", "")
            patronymic = pharmacist.pharmacy_info.get("patronymic", "")

            name_parts = []
            if last_name:
                name_parts.append(last_name)
            if first_name:
                name_parts.append(first_name)
            if patronymic:
                name_parts.append(patronymic)

            pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"

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

        await message.bot.send_document(
            chat_id=pharmacist.user.telegram_id,
            document=document.file_id,
            caption=(
                f"📄 <b>Получен документ с рецептом</b>\n\n"
                f"👤 <b>От пользователя:</b> {user_name}\n"
                f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
                f"❓ <b>По вопросу:</b> {question.text[:100] if question else 'Вопрос не найден'}...\n"
                f"{'💬 <b>Описание:</b> ' + message.caption if message.caption else ''}\n\n"
                f"⚠️ <i>Документ временный и не сохранен в системе</i>\n"
                f"💊 <i>Этот документ был запрошен вами у пользователя</i>"
            ),
            parse_mode="HTML",
            reply_markup=pharmacist_keyboard,
        )

        await DialogService.add_message(
            db=db,
            question_id=question_uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="photo",
            file_id=document.file_id,
            caption=message.caption,
        )

        await message.answer(
            f"✅ Документ с рецептом отправлен фармацевту {pharmacist_name}!\n\n"
            "Вы можете отправить еще файлы или нажмите /done чтобы завершить."
        )

    except Exception as e:
        logger.error(f"Error processing prescription document: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке документа")


@router.message(Command("done"), UserQAStates.waiting_for_prescription_photo)
async def finish_photo_upload(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Завершение загрузки фото рецепта"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")
        original_message_id = state_data.get("prescription_photo_message_id")

        if pharmacist_id:
            result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == pharmacist_id)
            )
            pharmacist = result.scalar_one_or_none()

            if pharmacist and pharmacist.user:
                user_name = user.first_name or "Пользователь"
                if user.last_name:
                    user_name = f"{user.first_name} {user.last_name}"

                await pharmacist.user.telegram_id and await message.bot.send_message(
                    chat_id=pharmacist.user.telegram_id,
                    text=(
                        f"✅ <b>Пользователь завершил загрузку фото</b>\n\n"
                        f"👤 {user_name} закончил отправку фото рецепта.\n"
                        f"Продолжайте консультацию."
                    ),
                    parse_mode="HTML",
                )

        await state.clear()

        if original_message_id:
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=original_message_id,
                    reply_markup=None,
                )
            except Exception:
                pass

        await message.answer(
            "✅ <b>Загрузка фото завершена</b>\n\n"
            "Фармацевт получит уведомление и ответит вам.",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in finish_photo_upload: {e}", exc_info=True)
        await state.clear()
        await message.answer("❌ Ошибка при завершении загрузки")
