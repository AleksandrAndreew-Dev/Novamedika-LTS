# qa_service.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid
from fastapi import HTTPException, status

from db.qa_models import Question, Answer
from db.qa_schemas import AnswerBase
from bot.core import bot_manager
from bot.services.dialog_service import DialogService  # ✅ ДОБАВИЛИ
from bot.keyboards.qa_keyboard import make_user_consultation_keyboard  # ✅ ДОБАВИЛИ

logger = logging.getLogger(__name__)

async def answer_question_internal(
    question_id: str,
    answer: AnswerBase,
    pharmacist,
    db: AsyncSession
):
    """Внутренняя функция для ответа на вопрос (используется ботом)"""
    try:
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # ✅ СОХРАНЯЕМ ОТВЕТ В ИСТОРИЮ ДИАЛОГА
        await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="pharmacist",
            sender_id=pharmacist.uuid,
            message_type="answer",
            text=answer.text
        )

        # Создаем запись ответа
        new_answer = Answer(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            text=answer.text
        )

        question.status = "answered"
        question.answered_by = pharmacist.uuid

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        # Отправка ответа пользователю
        await send_answer_to_user(question, answer.text, pharmacist, db)

        return new_answer

    except Exception as e:
        await db.rollback()
        logger.error(f"Error in answer_question_internal: {e}")
        raise

async def send_answer_to_user(question, answer_text: str, pharmacist, db: AsyncSession):
    """Отправка ответа пользователю в Telegram с полной историей"""
    try:
        bot, _ = await bot_manager.initialize()

        if not bot or not question.user or not question.user.telegram_id:
            logger.error("Cannot send answer: bot, user or telegram_id not available")
            return

        # ✅ Получаем полную историю диалога
        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question.uuid, db, include_header=False
        )

        # Формируем информацию о фармацевте
        pharmacy_info = getattr(pharmacist, "pharmacy_info", {}) or {}

        first_name = pharmacy_info.get("first_name", "")
        last_name = pharmacy_info.get("last_name", "")
        patronymic = pharmacy_info.get("patronymic", "")

        pharmacist_name_parts = []
        if last_name:
            pharmacist_name_parts.append(last_name)
        if first_name:
            pharmacist_name_parts.append(first_name)
        if patronymic:
            pharmacist_name_parts.append(patronymic)

        pharmacist_name = " ".join(pharmacist_name_parts) if pharmacist_name_parts else "Фармацевт"
        pharmacist_info_text = f"{pharmacist_name}"

        chain = pharmacy_info.get("chain", "")
        number = pharmacy_info.get("number", "")
        role = pharmacy_info.get("role", "Фармацевт")

        if chain and number:
            pharmacist_info_text += f", {chain}, аптека №{number}"
        if role and role != "Фармацевт":
            pharmacist_info_text += f" ({role})"

        # Формируем полное сообщение
        message_text = (
            f"💬 <b>ОТВЕТ ФАРМАЦЕВТА</b>\n\n"
            f"{history_text}\n\n"
            f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_info_text}"
        )

        # Отправляем сообщение пользователю С КНОПКАМИ
        await bot.send_message(
            chat_id=question.user.telegram_id,
            text=message_text,
            parse_mode="HTML",
            
        )

        logger.info(f"Answer sent to user {question.user.telegram_id} with full history")

    except Exception as e:
        logger.error(f"Failed to send answer to user: {e}")
