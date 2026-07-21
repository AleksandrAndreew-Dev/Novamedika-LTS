# bot/handlers/dialog_management.py
from typing import Optional

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from utils.time_utils import get_utc_now_naive

from db.qa_models import Question, User, Pharmacist
from bot.handlers.qa_states import QAStates, UserQAStates
from bot.keyboards.qa_keyboard import (
    make_completed_dialog_keyboard,
    get_post_consultation_keyboard,
)
from routers.pharmacist_dashboard import ws_manager, publish_to_redis

logger = logging.getLogger(__name__)
router = Router()


# Общая функция для завершения диалога (унифицированная)
async def complete_dialog_service(
    question_uuid: str,
    db: AsyncSession,
    initiator_type: str,
    initiator: User,
    callback: CallbackQuery = None,
    message: Message = None,
) -> bool:
    """Сервис завершения диалога - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # Получаем вопрос с информацией о фармацевте
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            if callback:
                await callback.answer("❌ Вопрос не найден", show_alert=True)
            elif message:
                await message.answer("❌ Вопрос не найден")
            return False

        # ✅ ВАЖНО: Сохраняем фармацевта ДО обнуления
        pharmacist_to_notify = None
        if initiator_type == "user" and question.taken_by:
            # Получаем фармацевта ПЕРЕД обнулением
            pharmacist_result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == question.taken_by)
            )
            pharmacist_to_notify = pharmacist_result.scalar_one_or_none()

        # ✅ УВЕДОМЛЕНИЕ: Если диалог уже завершен
        if question.status == "completed":
            if callback:
                await callback.answer(
                    "✅ Этот диалог уже завершен ранее", show_alert=True
                )
            return False

        # ✅ БЛОКИРОВКА: Запрещаем дальнейшие изменения после завершения
        question.status = "completed"
        question.answered_at = get_utc_now_naive()

        # ✅ ОЧИСТКА: Убираем фармацевта из взятых вопросов
        question.taken_by = None
        question.taken_at = None

        # ✅ ФЛАГ: Устанавливаем флаг полного завершения
        if not question.context_data:
            question.context_data = {}

        question.context_data["completed_by"] = initiator_type
        question.context_data["completed_at"] = get_utc_now_naive().isoformat()
        question.context_data["is_final"] = True  # Флаг окончательного завершения

        await db.commit()

        # Notify web chat via WebSocket and Redis cross-worker
        try:
            await ws_manager.broadcast_to_consultation(
                str(question.uuid),
                {
                    "type": "question_completed",
                    "question_id": str(question.uuid),
                    "completed_by": str(initiator.uuid),
                    "status": "completed",
                },
            )
        except Exception:
            pass

        try:
            await publish_to_redis(
                {
                    "type": "user_completion",
                    "question_id": str(question.uuid),
                    "completed_by": str(initiator.uuid),
                    "status": "completed",
                }
            )
        except Exception:
            pass

        # Минимальное исправление для уведомления пользователя
        if (
            initiator_type == "pharmacist"
            and question.user
            and question.user.telegram_id
        ):
            try:
                bot = None
                if message:
                    bot = message.bot
                elif callback:
                    bot = callback.bot

                if bot:
                    await bot.send_message(
                        chat_id=question.user.telegram_id,
                        text=(
                            f"✅ <b>Консультация завершена</b>\n\n"
                            f"Ваш вопрос: {question.text[:150]}...\n\n"
                            "Задайте новый вопрос, если нужно."
                        ),
                        parse_mode="HTML",
                        reply_markup=get_post_consultation_keyboard(),
                    )
            except Exception as e:
                logger.error(f"Ошибка уведомления пользователя: {e}")

        # ✅ Теперь уведомляем фармацевта (если есть)
        if (
            initiator_type == "user"
            and pharmacist_to_notify
            and pharmacist_to_notify.user
        ):
            try:
                # Формируем имя пользователя
                user_name = initiator.first_name or "Пользователь"
                if initiator.last_name:
                    user_name = f"{initiator.first_name} {initiator.last_name}"

                # Формируем имя фармацевта
                pharmacist_name = "Фармацевт"
                if pharmacist_to_notify.pharmacy_info:
                    first_name = pharmacist_to_notify.pharmacy_info.get(
                        "first_name", ""
                    )
                    last_name = pharmacist_to_notify.pharmacy_info.get("last_name", "")
                    patronymic = pharmacist_to_notify.pharmacy_info.get(
                        "patronymic", ""
                    )

                    name_parts = []
                    if last_name:
                        name_parts.append(last_name)
                    if first_name:
                        name_parts.append(first_name)
                    if patronymic:
                        name_parts.append(patronymic)

                    pharmacist_name = (
                        " ".join(name_parts) if name_parts else "Фармацевт"
                    )

                # Отправляем уведомление фармацевту
                await message.bot.send_message(
                    chat_id=pharmacist_to_notify.user.telegram_id,
                    text=(
                        f"🎯 <b>Пользователь завершил консультацию</b>\n\n"
                        f"Вопрос: {question.text[:200]}...\n\n"
                        f"Используйте /questions для новых вопросов"
                    ),
                    parse_mode="HTML",
                )
                logger.info(
                    f"Уведомление о завершении отправлено фармацевту {pharmacist_to_notify.user.telegram_id}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления фармацевту: {e}")

        return True

    except Exception as e:
        logger.error(f"Error in complete_dialog_service: {e}")
        return False


@router.callback_query(F.data.startswith("end_dialog_"))
async def end_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
):
    """Обработка нажатия кнопки завершения диалога - универсальный"""
    question_uuid = callback.data.replace("end_dialog_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if is_pharmacist:
            # Для фармацевта
            if question.taken_by != pharmacist.uuid:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return

            await callback.message.answer(
                f"⚠️ <b>Завершить диалог?</b>\n\n"
                f"Вопрос: {question.text[:200]}...\n\n"
                "Пользователь получит уведомление.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Завершить",
                                callback_data=f"confirm_end_{question_uuid}_pharmacist",
                            ),
                            InlineKeyboardButton(
                                text="❌ Нет",
                                callback_data=f"cancel_end_{question_uuid}",
                            ),
                        ]
                    ]
                ),
            )
        else:
            # Для пользователя
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

            await callback.message.answer(
                f"⚠️ <b>Завершение диалога</b>\n\n"
                f"Вы уверены, что хотите завершить диалог?\n\n"
                f"❓ Ваш вопрос: {question.text[:200]}...\n\n"
                f"После завершения фармацевт получит уведомление.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Завершить",
                                callback_data=f"confirm_end_{question_uuid}_user",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отмена",
                                callback_data=f"cancel_end_{question_uuid}",
                            ),
                        ]
                    ]
                ),
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in end_dialog_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("complete_consultation_"))
async def complete_consultation_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Обработка завершения консультации через кнопку в /complete"""
    if is_pharmacist:
        await callback.answer(
            "👨‍⚕️ Вы фармацевт. Используйте /end_dialog для завершения диалогов.",
            show_alert=True,
        )
        return

    question_uuid = callback.data.replace("complete_consultation_", "")

    try:
        # Получаем вопрос
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
            await callback.answer("✅ Эта консультация уже завершена", show_alert=True)
            return

        # Используем универсальную функцию завершения диалога
        success = await complete_dialog_service(
            question_uuid=question_uuid,
            db=db,
            initiator_type="user",
            initiator=user,
            callback=callback,
            message=callback.message,
        )

        if success:
            # ✅ ОЧИЩАЕМ СОСТОЯНИЕ ПОСЛЕ ЗАВЕРШЕНИЯ
            await state.clear()

            # Обновляем сообщение
            await callback.message.edit_text(
                f"✅ Консультация успешно завершена!\n\n"
                f"❓ Вопрос: {question.text[:100]}...\n\n"
                f"Теперь вы можете задать новый вопрос или посмотреть другие консультации.",
                parse_mode="HTML",
                reply_markup=make_completed_dialog_keyboard(),
            )
            await callback.answer()
        else:
            await callback.answer(
                "❌ Ошибка при завершении консультации", show_alert=True
            )

    except Exception as e:
        logger.error(f"Error in complete_consultation_callback: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.callback_query(F.data.startswith("confirm_end_"))
async def confirm_end_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
    state: FSMContext,
):
    """Подтверждение завершения диалога"""
    data = callback.data.replace("confirm_end_", "")
    parts = data.split("_")

    if len(parts) < 2:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    question_uuid = parts[0]
    initiator_type = parts[1]  # pharmacist или user

    try:
        # Используем универсальный сервис
        success = await complete_dialog_service(
            question_uuid=question_uuid,
            db=db,
            initiator_type=initiator_type,
            initiator=pharmacist if is_pharmacist else user,
            callback=callback,
            message=callback.message,
        )

        if success:
            # ✅ ОЧИЩАЕМ СОСТОЯНИЕ В ЛЮБОМ СЛУЧАЕ
            await state.clear()

            # Отправляем сообщение инициатору
            if initiator_type == "pharmacist":
                await callback.message.answer(
                    "✅ <b>Диалог завершен</b>\n\n"
                    "Пользователь уведомлен.\n"
                    "Используйте /questions для новых вопросов",
                    parse_mode="HTML",
                )
            else:
                await callback.message.answer(
                    "🎯 <b>ВАША КОНСУЛЬТАЦИЯ ЗАВЕРШЕНА</b>\n\n"
                    "✅ Фармацевт уведомлен о завершении диалога.\n\n"
                    "✨ Вы можете задать новый вопрос:",
                    parse_mode="HTML",
                    reply_markup=make_completed_dialog_keyboard(),
                )

            await callback.answer("✅ Диалог завершен")

    except Exception as e:
        logger.error(f"Error in confirm_end_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при завершении диалога", show_alert=True)


@router.callback_query(F.data.startswith("cancel_end_"))
async def cancel_end_dialog_callback(callback: CallbackQuery):
    """Отмена завершения диалога"""
    await callback.answer("❌ Завершение отменено")

    await callback.message.answer(
        "🔄 Диалог продолжается.\n" "Вы можете продолжить общение."
    )


# Команда для завершения диалога через меню
@router.message(Command("end_dialog"))
async def cmd_end_dialog(
    message: Message,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
):
    """Команда завершения диалога через меню"""
    try:
        if is_pharmacist:
            # Активные вопросы фармацевта
            result = await db.execute(
                select(Question)
                .where(
                    Question.taken_by == pharmacist.uuid,
                    Question.status.in_(["in_progress", "answered"]),
                )
                .order_by(Question.taken_at.desc())
            )
            questions = result.scalars().all()
        else:
            # Активные вопросы пользователя
            result = await db.execute(
                select(Question)
                .where(
                    Question.user_id == user.uuid,
                    Question.status.in_(["in_progress", "answered"]),
                )
                .order_by(Question.created_at.desc())
            )
            questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📭 У вас нет активных диалогов для завершения.",
                parse_mode="HTML",
            )
            return

        # Создаем клавиатуру с вопросами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions[:5]:
            question_preview = (
                question.text[:50] + "..." if len(question.text) > 50 else question.text
            )
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"❓ {question_preview}",
                        callback_data=f"end_dialog_{question.uuid}",
                    )
                ]
            )

        await message.answer(
            "📋 <b>Выберите диалог для завершения:</b>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(f"Error in cmd_end_dialog: {e}")
        await message.answer("❌ Ошибка при получении диалогов")
