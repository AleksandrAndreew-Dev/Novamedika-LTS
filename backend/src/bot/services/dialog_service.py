
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


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

            db.add(message)
            await db.flush()

            logger.info(
                f"Dialog message added: question_id={question_id}, type={message_type}, text='{text[:50] if text else ''}...'"
            )
            return message

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding dialog message: {e}", exc_info=True)
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
            logger.error(f"Error getting dialog history: {e}", exc_info=True)
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
            logger.error(f"Error getting question with dialog: {e}", exc_info=True)
            return None

    @staticmethod
    async def format_dialog_history_for_display(
        question_id: UUID,
        db: AsyncSession,
        limit: int = 20
    ) -> Tuple[str, List[str]]:
        """Форматировать историю диалога для отображения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Получаем историю диалога
            messages = await DialogService.get_dialog_history(question_id, db, limit)

            # ✅ ЛОГИРОВАНИЕ для отладки
            logger.info(f"Formatting dialog history for question {question_id}: {len(messages)} messages")

            if not messages:
                return "📋 <b>ИСТОРИЯ ДИАЛОГА</b>\n\n" \
                       "Пока что история диалога пуста. " \
                       "Все сообщения будут отображаться здесь по мере общения.\n\n" \
                       "━" * 30, []

            # Группируем сообщения
            formatted_messages = []
            file_ids = []

            current_date = None

            for msg in messages:
                # ✅ ЛОГИРОВАНИЕ каждого сообщения
                logger.info(f"Message: type={msg.message_type}, sender={msg.sender_type}, text='{msg.text[:50] if msg.text else 'None'}'")

                # Определяем отправителя и иконку
                if msg.sender_type == "user":
                    sender_icon = "👤"
                    sender_name = "Вы"
                else:
                    sender_icon = "👨‍⚕️"
                    sender_name = "Фармацевт"

                # Форматируем время
                time_str = msg.created_at.strftime("%H:%M")

                # Проверяем, изменилась ли дата
                message_date = msg.created_at.strftime("%d.%m.%Y")
                if current_date != message_date:
                    current_date = message_date
                    date_header = f"\n📅 <b>{current_date}</b>\n" + "─" * 30 + "\n"
                    formatted_messages.append(date_header)

                # Форматируем контент в зависимости от типа сообщения
                if msg.message_type == "question":
                    content = f"❓ <b>Вопрос:</b>\n{msg.text}"
                elif msg.message_type == "answer":
                    content = f"💬 <b>Ответ:</b>\n{msg.text}"
                elif msg.message_type == "clarification":
                    content = f"🔍 <b>Уточнение:</b>\n{msg.text}"
                elif msg.message_type == "photo":
                    content = "📸 <b>Фото рецепта</b>"
                    if msg.caption:
                        content += f"\n📝 <i>{msg.caption}</i>"
                    if msg.file_id:
                        file_ids.append(msg.file_id)
                else:
                    content = f"💭 <b>Сообщение:</b>\n{msg.text}"

                formatted_msg = f"{sender_icon} <b>{sender_name}</b> [{time_str}]\n{content}\n"
                formatted_messages.append(formatted_msg)

            # Собираем полную историю (новые сообщения внизу)
            history_text = "📋 <b>ПОЛНАЯ ИСТОРИЯ ДИАЛОГА</b>\n\n"

            # Добавляем все отформатированные сообщения
            for formatted_msg in formatted_messages:
                history_text += formatted_msg + "\n"

            # Добавляем разделитель в конце
            history_text += "━" * 30

            # ✅ ЛОГИРОВАНИЕ результата
            logger.info(f"Formatted history length: {len(history_text)} chars")

            return history_text, file_ids

        except Exception as e:
            logger.error(f"Error formatting dialog history: {e}", exc_info=True)
            return "📋 <b>ИСТОРИЯ ДИАЛОГА</b>\n\n" \
                   "❌ Не удалось загрузить историю диалога.\n\n" \
                   "━" * 30, []
