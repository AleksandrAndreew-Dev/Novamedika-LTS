import logging
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
    async def remove_photos_from_dialog(
        question_id: UUID, db: AsyncSession, sender_type: Optional[str] = None
    ) -> int:
        """Удалить фото из истории диалога (пометить как удалённые)"""
        try:
            query = (
                select(DialogMessage)
                .where(DialogMessage.question_id == question_id)
                .where(DialogMessage.message_type == "photo")
                .where(DialogMessage.is_deleted == False)
            )
            if sender_type:
                query = query.where(DialogMessage.sender_type == sender_type)

            result = await db.execute(query)
            messages = result.scalars().all()

            count = 0
            for msg in messages:
                msg.is_deleted = True
                count += 1

            logger.info(f"Removed {count} photos from dialog {question_id}")
            return count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error removing photos from dialog: {e}", exc_info=True)
            return 0

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
        question_id: UUID, db: AsyncSession, limit: int = 20
    ) -> Tuple[str, List[str]]:
        """Форматировать историю диалога для отображения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Получаем историю диалога
            messages = await DialogService.get_dialog_history(question_id, db, limit)

            # ✅ ЛОГИРОВАНИЕ для отладки
            logger.info(
                f"Formatting dialog history for question {question_id}: {len(messages)} messages"
            )

            if not messages:
                return (
                    "📋 <b>ИСТОРИЯ ДИАЛОГА</b>\n\n"
                    "Пока что история диалога пуста. "
                    "Все сообщения будут отображаться здесь по мере общения.\n\n"
                    "━" * 30,
                    [],
                )

            # Группируем сообщения
            formatted_messages = []
            file_ids = []

            current_date = None

            for msg in messages:
                # ✅ ЛОГИРОВАНИЕ каждого сообщения
                logger.info(
                    f"Message: type={msg.message_type}, sender={msg.sender_type}, text='{msg.text[:50] if msg.text else 'None'}'"
                )

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

                formatted_msg = (
                    f"{sender_icon} <b>{sender_name}</b> [{time_str}]\n{content}\n"
                )
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
            return (
                "📋 <b>ИСТОРИЯ ДИАЛОГА</b>\n\n"
                "❌ Не удалось загрузить историю диалога.\n\n"
                "━" * 30,
                [],
            )

    @staticmethod
    async def send_unified_dialog_history(
        bot,
        chat_id: int,
        question_uuid: str,
        db: AsyncSession,
        title: str = "ПОЛНАЯ ИСТОРИЯ ДИАЛОГА",
        pre_text: Optional[str] = None,
        post_text: Optional[str] = None,
        is_pharmacist: bool = False,
        show_buttons: bool = True,
        custom_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
    ) -> str:
        """Универсальная функция отправки полной истории диалога - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Получаем полную историю диалога
            history_text, file_ids = (
                await DialogService.format_dialog_history_for_display(
                    question_uuid, db, limit=20
                )
            )

            # Формируем сообщение
            message_parts = []
            if pre_text:
                message_parts.append(pre_text)

            message_parts.append(f"📋 <b>{title}</b>\n\n{history_text}")

            if post_text:
                message_parts.append(post_text)

            message_text = "\n\n".join(message_parts)

            # Создаем клавиатуру
            reply_markup = None
            if show_buttons:
                if custom_buttons:
                    # Используем кастомные кнопки
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=custom_buttons)
                elif is_pharmacist:
                    # Стандартные кнопки для фармацевта
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="💬 Ответить",
                                    callback_data=f"answer_{question_uuid}",
                                ),
                                InlineKeyboardButton(
                                    text="📸 Запросить фото",
                                    callback_data=f"request_photo_{question_uuid}",
                                ),
                            ],
                            [
                                InlineKeyboardButton(
                                    text="✅ Завершить диалог",
                                    callback_data=f"end_dialog_{question_uuid}",
                                )
                            ],
                        ]
                    )
                else:
                    # Стандартные кнопки для пользователя
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✍️ Ответить",
                                    callback_data=f"continue_user_dialog_{question_uuid}",
                                ),
                                InlineKeyboardButton(
                                    text="✅ Завершить",
                                    callback_data=f"end_dialog_{question_uuid}",
                                ),
                            ],
                        ]
                    )

            # Отправляем сообщение
            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            # Отправляем фото, если есть
            for file_id in file_ids[:3]:  # Ограничиваем 3 фото
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=file_id,
                        caption="📸 Фото из истории диалога",
                    )
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")

            return history_text

        except Exception as e:
            logger.error(f"Error in send_unified_dialog_history: {e}", exc_info=True)
            error_msg = f"📋 <b>{title}</b>\n\n❌ Не удалось загрузить историю диалога."
            await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="HTML")
            return error_msg
