# bot/handlers/direct_questions.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from db.qa_models import User, Question
from utils.time_utils import get_utc_now_naive
from bot.services.notification_service import notify_pharmacists_about_new_question

logger = logging.getLogger(__name__)
router = Router()

# Список общих фраз, которые НЕ должны создавать вопросы
IGNORE_PHRASES = {
    'привет', 'здравствуйте', 'здравствуй', 'добрый день', 'добрый вечер',
    'доброе утро', 'hi', 'hello', 'start', 'начать', 'спасибо', 'благодарю',
    'ок', 'хорошо', 'понятно', 'ясно', 'ага', 'угу', 'да', 'нет', 'может быть',
    'возможно', 'наверное', 'ладно', 'хм', 'а', 'э', 'ого', 'вау', 'круто',
    'супер', 'отлично', 'класс', 'прекрасно', 'замечательно', 'отлично'
}

def should_create_question(text: str) -> bool:
    """Определяет, стоит ли создавать вопрос из текста"""
    text_lower = text.lower().strip()

    # 1. Проверяем на игнорируемые фразы
    if text_lower in IGNORE_PHRASES:
        return False

    # 2. Проверяем длину (минимально 5 символов)
    if len(text_lower) < 5:
        return False

    # 3. Проверяем, что это не просто набор символов или цифр
    if text_lower.replace('?', '').replace('!', '').replace('.', '').replace(',', '').strip().isdigit():
        return False

    # 4. Проверяем на явные команды (даже без /)
    if text_lower.startswith(('список', 'помощь', 'команды', 'меню', 'старт')):
        return False

    return True

@router.message(F.text & ~F.command)
async def handle_direct_text(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext
):
    """Обработка прямых текстовых сообщений как вопросов"""

    # Пропускаем фармацевтов
    if is_pharmacist:
        return

    # Проверяем состояние
    current_state = await state.get_state()
    if current_state is not None:
        return

    # Проверяем, стоит ли создавать вопрос
    if not should_create_question(message.text):
        return

    try:
        # Создаем вопрос
        question = Question(
            text=message.text,
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive()
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        logger.info(f"Direct question from {user.telegram_id}: {message.text[:50]}...")

        # Уведомляем фармацевтов
        await notify_pharmacists_about_new_question(question, db)

        # Подтверждение пользователю
        await message.answer(
            "✅ <b>Вопрос отправлен!</b>\n\n"
            "Фармацевты уже получили уведомление.\n"
            "<i>Используйте /clarify если нужно уточнить</i>",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in direct question: {e}")


