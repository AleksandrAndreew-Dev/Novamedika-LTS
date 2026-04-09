from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import SkipHandler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from db.qa_models import User, Question
from utils.time_utils import get_utc_now_naive
from bot.services.notification_service import notify_pharmacists_about_new_question
from bot.handlers.qa_states import UserQAStates
from bot.services.dialog_service import DialogService
from bot.handlers.user_question_handlers.message_handlers import process_dialog_message
from bot.keyboards.qa_keyboard import get_post_consultation_keyboard

logger = logging.getLogger(__name__)
router = Router()


def should_create_question(text: str) -> bool:
    """Определяет, стоит ли создавать вопрос из текста"""
    text_lower = text.lower().strip()

    # 0. Проверяем, является ли это командой (начинается с /)
    if text.startswith("/"):
        return False

    # 2. Проверяем длину (минимально 2 символов)
    if len(text_lower) < 2:
        return False

    # 3. Проверяем, что это не просто набор символов или цифр
    if (
        text_lower.replace("?", "")
        .replace("!", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
        .isdigit()
    ):
        return False

    # 4. Проверяем на явные команды (даже без /)
    if text_lower.startswith(("список", "помощь", "команды", "меню", "старт")):
        return False

    return True


@router.message(F.text & ~F.command)
async def handle_direct_text(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Обработка прямых текстовых сообщений как вопросов"""

    if is_pharmacist:
        logger.debug("handle_direct_text: skipping pharmacist message")
        raise SkipHandler()

    current_state = await state.get_state()
    logger.debug(
        "handle_direct_text: user=%s, state=%s, text='%s'",
        user.uuid,
        current_state,
        message.text[:50] if message.text else "None",
    )

    # ✅ ПРОВЕРКА: Если у пользователя есть активные консультации
    if current_state is None:
        result = await db.execute(
            select(Question)
            .where(
                Question.user_id == user.uuid,
                Question.status.in_(["in_progress", "answered"]),
                Question.taken_by.is_not(None),
            )
            .order_by(Question.answered_at.desc())
            .limit(1)
        )
        active_question = result.scalar_one_or_none()

        if active_question:
            if active_question.status == "completed":
                await state.clear()
            else:
                await state.update_data(
                    active_dialog_question_id=str(active_question.uuid)
                )
                await state.set_state(UserQAStates.in_dialog)
                await process_dialog_message(message, state, db, user, is_pharmacist)
                return

    # ✅ ПРОВЕРКА: Если состояние указывает на завершенный диалог
    if current_state == UserQAStates.in_dialog:
        state_data = await state.get_data()
        question_uuid = state_data.get("active_dialog_question_id")

        if question_uuid:
            result = await db.execute(
                select(Question).where(Question.uuid == question_uuid)
            )
            question = result.scalar_one_or_none()
            if question and question.status == "completed":
                await state.clear()
                current_state = None

    # Если пользователь в состоянии, которое обрабатывается другим хендлером — пропускаем
    if current_state is not None:
        if current_state in [
            UserQAStates.waiting_for_prescription_photo,
            UserQAStates.waiting_for_clarification,
            UserQAStates.in_dialog,
            UserQAStates.waiting_for_question,
        ]:
            logger.debug(
                "handle_direct_text: skipping, user in state %s", current_state
            )
            raise SkipHandler()

        # Для других состояний сбрасываем
        await state.clear()

    # Проверяем текст
    if not message.text or not message.text.strip():
        logger.debug("handle_direct_text: empty text, skipping")
        raise SkipHandler()

    if not should_create_question(message.text):
        logger.debug(
            "handle_direct_text: should_create_question=False for '%s'",
            message.text[:50],
        )
        raise SkipHandler()

    # Создаём вопрос
    try:
        logger.info("Creating question from text: '%s'", message.text[:80])

        question = Question(
            text=message.text,
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive(),
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        logger.info(
            "Direct question created: ID=%s, text='%s...'",
            question.uuid,
            question.text[:50],
        )

        dialog_message = await DialogService.create_question_message(question, db)
        await db.commit()

        logger.info(
            "Dialog message created: question_id=%s, type=%s",
            dialog_message.question_id,
            dialog_message.message_type,
        )

        await notify_pharmacists_about_new_question(question, db)

        await message.answer(
            "✅ <b>Вопрос отправлен!</b>\n\n"
            "Фармацевты получили уведомление и скоро ответят.\n\n"
            "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in direct question: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при отправке вопроса. Пожалуйста, попробуйте еще раз.",
            parse_mode="HTML",
        )
