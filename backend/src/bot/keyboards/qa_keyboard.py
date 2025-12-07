from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)


# qa_keyboard.py - НОВЫЕ КЛАВИАТУРЫ

def make_user_consultation_keyboard(question_uuid: str) -> InlineKeyboardMarkup:
    """Клавиатура для пользователя после ответа фармацевта"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Уточнить вопрос",
                    callback_data=f"quick_clarify_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📸 Отправить фото рецепта",
                    callback_data=f"send_prescription_photo_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить консультацию",
                    callback_data=f"complete_consultation_{question_uuid}"
                )
            ]
        ]
    )

def make_completed_dialog_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после завершения диалога"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Задать новый вопрос",
                    callback_data="ask_new_question"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств",
                    callback_data="search_drugs"
                ),
                InlineKeyboardButton(
                    text="📖 Мои вопросы",
                    callback_data="my_questions"
                )
            ]
        ]
    )

def make_question_list_keyboard(question_uuid: str):
    """Клавиатура для вопроса в списке (до взятия)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Ответить", callback_data=f"answer_{question_uuid}"
                )
            ]
        ]
    )


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


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# В qa_keyboard.py добавить/обновить функции:


def make_pharmacist_dialog_keyboard(question_uuid: str):
    """Клавиатура для фармацевта в диалоге С КНОПКОЙ ЗАВЕРШЕНИЯ"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Запросить фото рецепта",
                    callback_data=f"request_photo_{question_uuid}",
                ),
                InlineKeyboardButton(
                    text="💬 Ответить", callback_data=f"answer_{question_uuid}"
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


def make_user_dialog_keyboard_with_end(
    question_uuid: str, photo_requested: bool = False
):
    """Клавиатура для пользователя в диалоге С КНОПКОЙ ЗАВЕРШЕНИЯ"""
    buttons = []

    # Кнопка уточнения
    buttons.append(
        [
            InlineKeyboardButton(
                text="✍️ Уточнить вопрос", callback_data=f"quick_clarify_{question_uuid}"
            )
        ]
    )

    # Кнопка фото только если запрошено
    if photo_requested:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📸 Отправить фото рецепта",
                    callback_data=f"send_prescription_photo_{question_uuid}",
                )
            ]
        )

    # Кнопка завершения диалога
    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Завершить диалог", callback_data=f"end_dialog_{question_uuid}"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
