from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)


def make_question_keyboard(question_uuid: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой ответа на вопрос

    Args:
        question_uuid: UUID вопроса для callback_data

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой "Ответить"
    """
    try:
        # Создаем кнопку "Ответить"
        answer_button = InlineKeyboardButton(
            text="💬 Ответить на вопрос", callback_data=f"answer_{question_uuid}"
        )

        # Создаем клавиатуру с одной кнопкой
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[answer_button]])

        logger.debug(f"Created keyboard for question {question_uuid}")
        return keyboard

    except Exception as e:
        logger.error(f"Error creating question keyboard for {question_uuid}: {e}")
        # Возвращаем пустую клавиатуру в случае ошибки
        return InlineKeyboardMarkup(inline_keyboard=[])
