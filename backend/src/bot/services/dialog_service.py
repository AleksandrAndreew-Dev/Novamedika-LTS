# services/dialog_service.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from db.qa_models import DialogMessage, Question
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)


class DialogService:

    @staticmethod
    async def add_message(
        db: AsyncSession,
        question_id: UUID,
        sender_type: str,
        sender_id: UUID,
        message_type: str,
        text: Optional[str] = None,
        file_id: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> DialogMessage:
        """Добавить сообщение в историю диалога"""
        try:
            message = DialogMessage(
                question_id=question_id,
                message_type=message_type,
                sender_type=sender_type,
                sender_id=sender_id,
                text=text,
                file_id=file_id,
                caption=caption,
                created_at=get_utc_now_naive(),
            )

            await db.flush()

            logger.info(
                f"Dialog message added: question_id={question_id}, type={message_type}"
            )
            return message

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding dialog message: {e}")
            raise

    @staticmethod
    async def get_dialog_history(
        question_id: UUID, db: AsyncSession, limit: int = 100
    ) -> List[DialogMessage]:
        """Получить полную историю диалога по вопросу"""
        try:
            result = await db.execute(
                select(DialogMessage)
                .where(DialogMessage.question_id == question_id)
                .where(DialogMessage.is_deleted == False)
                .order_by(DialogMessage.created_at.asc())
                .limit(limit)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting dialog history: {e}")
            return []

    @staticmethod
    async def create_question_message(
        question: Question, db: AsyncSession
    ) -> DialogMessage:
        """Создать первое сообщение - сам вопрос"""
        return await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="user",
            sender_id=question.user_id,
            message_type="question",
            text=question.text,
        )

    @staticmethod
    async def get_question_with_dialog(
        question_id: UUID, db: AsyncSession
    ) -> Optional[Question]:
        """Получить вопрос со всей историей диалога"""
        try:
            result = await db.execute(
                select(Question)
                .options(selectinload(Question.dialog_messages))
                .where(Question.uuid == question_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting question with dialog: {e}")
            return None

    @staticmethod
    async def format_dialog_history_for_display(
        question_id: UUID,
        db: AsyncSession,
        limit: int = 50
    ) -> Tuple[str, List[str]]:
        """Форматировать историю диалога для отображения"""
        try:
            # Получаем историю диалога
            messages = await DialogService.get_dialog_history(question_id, db, limit)

            if not messages:
                return "История диалога пуста.", []

            # Группируем сообщения по датам
            formatted_messages = []
            file_ids = []

            for msg in messages:
                # Определяем отправителя и иконку
                if msg.sender_type == "user":
                    sender_icon = "👤"
                    sender_name = "Вы"
                else:
                    sender_icon = "👨‍⚕️"
                    sender_name = "Фармацевт"

                # Форматируем время
                time_str = msg.created_at.strftime("%H:%M")

                if msg.message_type == "question":
                    content = f"❓ Вопрос: {msg.text}"
                elif msg.message_type == "answer":
                    content = f"💬 Ответ: {msg.text}"
                elif msg.message_type == "clarification":
                    content = f"🔍 Уточнение: {msg.text}"
                elif msg.message_type == "photo":
                    content = "📸 Фото рецепта"
                    if msg.caption:
                        content += f": {msg.caption}"
                    if msg.file_id:
                        file_ids.append(msg.file_id)
                else:
                    content = f"💭 Сообщение: {msg.text}"

                formatted_msg = (
                    f"{sender_icon} <b>{sender_name}</b> [{time_str}]\n"
                    f"{content}"
                )
                formatted_messages.append(formatted_msg)

            # Собираем полную историю
            history_text = "<b>📋 ПОЛНАЯ ИСТОРИЯ ДИАЛОГА</b>\n"
            history_text += "━" * 30 + "\n\n"

            for i, msg in enumerate(reversed(formatted_messages), 1):
                history_text += f"{msg}\n\n"
                if i < len(formatted_messages):
                    history_text += "―" * 20 + "\n\n"

            return history_text, file_ids

        except Exception as e:
            logger.error(f"Error formatting dialog history: {e}")
            return "❌ Не удалось загрузить историю диалога.", []
