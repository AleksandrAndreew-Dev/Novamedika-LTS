"""Utility functions for creating questions from direct text messages.
No router handlers here — called from unknown_command as a fallback."""

from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from db.qa_models import User, Question, Pharmacist
from utils.time_utils import get_utc_now_naive
from bot.services.notification_service import notify_pharmacists_about_new_question
from bot.handlers.qa_states import UserQAStates
from bot.services.dialog_service import DialogService
from bot.keyboards.qa_keyboard import make_pharmacist_dialog_keyboard

logger = logging.getLogger(__name__)


def should_create_question(text: str) -> bool:
    """Определяет, стоит ли создавать вопрос из текста"""
    text_lower = text.lower().strip()

    if text.startswith("/"):
        return False

    if len(text_lower) < 2:
        return False

    if (
        text_lower.replace("?", "")
        .replace("!", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
        .isdigit()
    ):
        return False

    if text_lower.startswith(("список", "помощь", "команды", "меню", "старт")):
        return False

    return True


async def _process_active_dialog_message(
    message: Message,
    db: AsyncSession,
    user: User,
    active_question: Question,
):
    """Отправить сообщение пользователя фармацевту в рамках активного диалога."""
    try:
        # Сохраняем сообщение в историю
        await DialogService.add_message(
            db=db,
            question_id=active_question.uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="message",
            text=message.text,
        )
        await db.commit()

        # Находим фармацевта
        pharmacist_result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == active_question.taken_by)
        )
        pharmacist = pharmacist_result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            logger.warning("No pharmacist for question %s", active_question.uuid)
            await message.answer("❌ Фармацевт не найден для этого диалога.")
            return

        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        pharmacist_name = "Фармацевт"
        if pharmacist.pharmacy_info:
            first = pharmacist.pharmacy_info.get("first_name", "")
            last = pharmacist.pharmacy_info.get("last_name", "")
            patr = pharmacist.pharmacy_info.get("patronymic", "")
            parts = [p for p in [last, first, patr] if p]
            pharmacist_name = " ".join(parts) if parts else "Фармацевт"

        # Отправляем фармацевту
        await DialogService.send_unified_dialog_history(
            bot=message.bot,
            chat_id=pharmacist.user.telegram_id,
            question_uuid=active_question.uuid,
            db=db,
            title="СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ",
            pre_text=(
                f"💬 <b>СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_name}\n"
                f"❓ <b>По вопросу:</b>\n{active_question.text[:150]}...\n\n"
                f"💭 <b>Сообщение:</b>\n{message.text}\n\n"
            ),
            post_text=None,
            is_pharmacist=True,
            show_buttons=True,
            custom_buttons=make_pharmacist_dialog_keyboard(
                active_question.uuid
            ).inline_keyboard,
        )

        # Подтверждение пользователю
        await message.answer(
            f"✅ Сообщение отправлено фармацевту {pharmacist_name}.\n\n"
            "Ожидайте ответа.",
        )

    except Exception as e:
        logger.error("Error in _process_active_dialog_message: %s", e, exc_info=True)
        await message.answer("❌ Ошибка при отправке сообщения. Попробуйте ещё раз.")


async def try_create_question(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
) -> bool:
    """Попытка создать вопрос из текстового сообщения.
    Возвращает True если вопрос создан/обработан, False если нет."""

    if is_pharmacist:
        return False

    current_state = await state.get_state()
    logger.debug(
        "try_create_question: user=%s, state=%s, text='%s'",
        user.uuid,
        current_state,
        message.text[:50] if message.text else "None",
    )

    # Проверяем активные консультации (in_progress или answered)
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
        logger.info(
            "User %s has active question %s, sending message",
            user.uuid,
            active_question.uuid,
        )
        await _process_active_dialog_message(message, db, user, active_question)
        return True

    # Нет активного вопроса — проверяем состояния
    if current_state is not None:
        if current_state in [
            UserQAStates.waiting_for_prescription_photo,
            UserQAStates.waiting_for_clarification,
            UserQAStates.in_dialog,
            UserQAStates.waiting_for_question,
        ]:
            logger.debug("try_create_question: skip, state=%s", current_state)
            return False
        await state.clear()

    # Проверяем текст
    if not message.text or not message.text.strip():
        return False

    if not should_create_question(message.text):
        return False

    # Создаём новый вопрос
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

        logger.info("Question created: ID=%s", question.uuid)

        await DialogService.create_question_message(question, db)
        await db.commit()

        await notify_pharmacists_about_new_question(question, db)

        await message.answer(
            "✅ <b>Вопрос отправлен!</b>\n\n"
            "Фармацевты получили уведомление и скоро ответят.\n\n"
            "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
            parse_mode="HTML",
        )
        return True

    except Exception as e:
        logger.error("Error creating question: %s", e, exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при отправке вопроса. Попробуйте ещё раз.",
            parse_mode="HTML",
        )
        return True
