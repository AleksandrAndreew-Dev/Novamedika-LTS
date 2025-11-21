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


def make_pharmacist_info_keyboard(pharmacist) -> InlineKeyboardMarkup:
    """Создает клавиатуру с информацией о фармацевте"""
    try:
        pharmacy_info = pharmacist.pharmacy_info or {}
        chain = pharmacy_info.get("chain", "Не указана")
        number = pharmacy_info.get("number", "Не указан")
        role = pharmacy_info.get("role", "Фармацевт")

        info_text = f"{chain}, аптека №{number}"
        if role:
            info_text += f" ({role})"

        info_button = InlineKeyboardButton(
            text="ℹ️ Информация о фармацевте",
            callback_data=f"pharmacist_info_{pharmacist.uuid}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[info_button]])
        return keyboard

    except Exception as e:
        logger.error(f"Error creating pharmacist info keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[])
