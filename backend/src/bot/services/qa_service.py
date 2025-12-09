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


# bot/services/qa_service.py - исправленная функция send_answer_to_user
async def send_answer_to_user(question, answer_text: str, pharmacist, db: AsyncSession):
    """Отправка ответа пользователю в Telegram с историей"""
    try:
        bot, _ = await bot_manager.initialize()

        if not bot or not question.user or not question.user.telegram_id:
            logger.error("Cannot send answer: bot, user or telegram_id not available")
            return

        # Формируем информацию о фармацевте
        pharmacy_info = getattr(pharmacist, "pharmacy_info", {}) or {}

        # Получаем историю диалога
        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question.uuid, db
        )

        # Создаем отформатированное сообщение с историей
        message_text = (
            "💊 <b>ПОЛУЧЕН ОТВЕТ НА ВАШ ВОПРОС!</b>\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
            f"💬 <b>Ответ:</b>\n{answer_text}\n"
        )

        # Добавляем историю диалога, если она есть
        if history_text and history_text != "История диалога пуста.":
            message_text += "\n\n" + history_text

        # Информация о фармацевте
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
        pharmacist_info = f"{pharmacist_name}"

        chain = pharmacy_info.get("chain", "")
        number = pharmacy_info.get("number", "")
        role = pharmacy_info.get("role", "Фармацевт")

        if chain and number:
            pharmacist_info += f", {chain}, аптека №{number}"
        if role and role != "Фармацевт":
            pharmacist_info += f" ({role})"

        message_text += f"\n\n👨‍⚕️ <b>Ответ предоставил:</b> {pharmacist_info}"

        # Клавиатура с кнопкой истории
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✍️ Уточнить этот вопрос",
                        callback_data=f"quick_clarify_{question.uuid}"
                    ),
                    InlineKeyboardButton(
                        text="✅ Завершить консультацию",
                        callback_data=f"end_dialog_{question.uuid}"
                    )
                ]
            ]
        )

        await bot.send_message(
            chat_id=question.user.telegram_id,
            text=message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Если в истории были фото, просто упоминаем об этом
        if file_ids:
            await bot.send_message(
                chat_id=question.user.telegram_id,
                text="📸 <i>В истории диалога были переданы фото рецепта</i>",
                parse_mode="HTML"
            )

        logger.info(f"Answer sent to user {question.user.telegram_id} with history")

    except Exception as e:
        logger.error(f"Failed to send answer to user: {e}")
