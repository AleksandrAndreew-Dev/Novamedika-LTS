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

        question.status = 'answered'
        question.answered_by = pharmacist.uuid

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        # Отправка ответа пользователю
        await send_answer_to_user(question, answer.text, db)

        return new_answer

    except Exception as e:
        await db.rollback()
        logger.error(f"Error in answer_question_internal: {e}")
        raise

async def send_answer_to_user(question, answer_text: str, db: AsyncSession):
    """Отправка ответа пользователю в Telegram"""
    try:
        from bot.core import bot_manager
        bot, _ = await bot_manager.initialize()

        if not bot:
            logger.error("Bot not initialized for sending answer to user")
            return

        if question.user.telegram_id:
            message_text = (
                "💊 Получен ответ на ваш вопрос!\n\n"
                f"❓ Ваш вопрос: {question.text}\n\n"
                f"💬 Ответ фармацевта: {answer_text}\n\n"
                "Спасибо, что пользуйтесь нашим сервисом! ❤️"
            )

            await bot.send_message(
                chat_id=question.user.telegram_id,
                text=message_text
            )
            logger.info(f"Answer sent to user {question.user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send answer to user: {e}")
