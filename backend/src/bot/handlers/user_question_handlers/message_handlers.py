"""Обработчики сообщений пользователя: вопросы и диалог."""

import logging

from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.qa_models import User, Question, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers import get_user_inline_keyboard
from bot.services.notification_service import notify_pharmacists_about_new_question
from bot.services.dialog_service import DialogService
from bot.handlers.direct_questions import send_user_message_to_pharmacist
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.message(UserQAStates.waiting_for_question)
async def process_user_question(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Упрощенная обработка вопроса от пользователя"""
    logger.info(f"Processing question from user {message.from_user.id}")

    if not message.text or not message.text.strip():
        await message.answer(
            "❌ Вопрос не может быть пустым. Пожалуйста, напишите текст вопроса."
        )
        await state.clear()
        return

    if is_pharmacist:
        await message.answer(
            "ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы."
        )
        await state.clear()
        return

    try:
        question = Question(
            text=message.text.strip(),
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive(),
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        await DialogService.create_question_message(question, db)

        logger.info(
            f"Question created for user {user.telegram_id}, question_id: {question.uuid}"
        )

        try:
            await notify_pharmacists_about_new_question(question, db)
        except Exception as e:
            logger.error(f"Error in notification service: {e}")

        await message.answer(
            "✅ <b>Вопрос отправлен</b>\n\n"
            "Фармацевт ответит как только освободится.",
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )
        await state.clear()

    except Exception as e:
        logger.error(
            f"Error processing question from user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer(
            "❌ <b>Не удалось отправить вопрос</b>\n\n"
            "Попробуйте еще раз через несколько минут.",
            parse_mode="HTML",
        )
        await state.clear()


@router.message(UserQAStates.in_dialog)
async def process_dialog_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Обработка сообщений пользователя в активном диалоге"""
    if is_pharmacist:
        await message.answer("👨‍⚕️ Вы фармацевт. Используйте /questions для ответов.")
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("active_dialog_question_id")

        if not question_uuid:
            await message.answer(
                "❌ Не найден активный диалог. "
                "Используйте /my_questions для продолжения."
            )
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await message.answer("❌ Диалог не найден или недоступен.")
            await state.clear()
            return

        if question.status == "completed":
            await message.answer(
                "❌ Эта консультация уже завершена.\n"
                "Вы не можете отправлять сообщения в завершенную консультацию.\n"
                "Используйте /ask для нового вопроса."
            )
            await state.clear()
            return

        if not question.taken_by:
            await message.answer("❌ Фармацевт не назначен для этого диалога.")
            return

        # Используем унифицированную функцию
        success = await send_user_message_to_pharmacist(message, db, user, question)

        if not success:
            logger.warning(
                f"Failed to send message to pharmacist for question {question_uuid}"
            )

    except Exception as e:
        logger.error(f"Error in process_dialog_message: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке сообщения. Попробуйте еще раз.")
