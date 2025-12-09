
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


async def send_answer_to_user(question, answer_text: str, pharmacist, db: AsyncSession):
    """Отправка ответа пользователю в Telegram с историей"""
    try:
        bot, _ = await bot_manager.initialize()

        if not bot or not question.user or not question.user.telegram_id:
            logger.error("Cannot send answer: bot, user or telegram_id not available")
            return

        # Формируем информацию о фармацевте
        pharmacy_info = getattr(pharmacist, "pharmacy_info", {}) or {}

        # Получаем последние 3 сообщения для превью
        recent_messages = await DialogService.get_dialog_history(question.uuid, db, limit=3)

        # Формируем превью истории
        history_preview = ""
        if recent_messages:
            history_preview = "\n\n📜 <b>Последние сообщения:</b>\n"
            for msg in reversed(recent_messages):
                if msg.sender_type == "user":
                    sender = "👤 Вы"
                else:
                    sender = "👨‍⚕️ Фармацевт"

                time_str = msg.created_at.strftime("%H:%M")

                if msg.message_type == "question":
                    preview = f"❓ {msg.text[:50]}..." if len(msg.text) > 50 else f"❓ {msg.text}"
                elif msg.message_type == "answer":
                    preview = f"💬 {msg.text[:50]}..." if len(msg.text) > 50 else f"💬 {msg.text}"
                elif msg.message_type == "photo":
                    preview = "📸 Фото рецепта"
                else:
                    preview = f"💭 {msg.text[:50]}..." if len(msg.text) > 50 else f"💭 {msg.text}"

                history_preview += f"{sender} [{time_str}]: {preview}\n"

        # Полное сообщение
        message_text = (
            "💊 <b>ПОЛУЧЕН ОТВЕТ НА ВАШ ВОПРОС!</b>\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
            f"💬 <b>Ответ:</b>\n{answer_text}\n"
        )

        if history_preview:
            message_text += history_preview

        message_text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"

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

        message_text += f"👨‍⚕️ <b>Ответ предоставил:</b> {pharmacist_info}\n\n"
        message_text += "💡 <i>Вы можете посмотреть полную историю диалога или уточнить вопрос</i>"

        # Клавиатура с кнопкой истории
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Полная история диалога",
                        callback_data=f"show_history_{question.uuid}"
                    )
                ],
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

        logger.info(f"Answer sent to user {question.user.telegram_id} with history")

    except Exception as e:
        logger.error(f"Failed to send answer to user: {e}")

