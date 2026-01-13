from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import WebAppInfo


import logging

logger = logging.getLogger(__name__)


def get_post_consultation_keyboard():
    """Клавиатура после завершения консультации"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Новый вопрос",
                    callback_data="ask_new_question"
                ),
                InlineKeyboardButton(
                    text="📋 Мои вопросы",
                    callback_data="my_questions"
                )
            ],
            [
                InlineKeyboardButton(
    text="🔍 Поиск лекарств",
    web_app = WebAppInfo(url="https://spravka.novamedika.com/")
),
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="user_help"
                )
            ]
        ]
    )


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
    web_app = WebAppInfo(url="https://spravka.novamedika.com/")
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


def make_dialog_history_keyboard(question_uuid: str, is_pharmacist: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра истории диалога"""
    if is_pharmacist:
        buttons = [
            [
                InlineKeyboardButton(
                    text="📋 Полная история диалога",
                    callback_data=f"show_history_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Продолжить общение",
                    callback_data=f"answer_{question_uuid}"
                ),
                InlineKeyboardButton(
                    text="📸 Запросить фото",
                    callback_data=f"request_photo_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить диалог",
                    callback_data=f"end_dialog_{question_uuid}"
                )
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(
                    text="📋 Полная история диалога",
                    callback_data=f"show_history_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✍️ Уточнить",
                    callback_data=f"quick_clarify_{question_uuid}"
                ),
                InlineKeyboardButton(
                    text="📸 Отправить фото",
                    callback_data=f"send_prescription_photo_{question_uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить консультацию",
                    callback_data=f"end_dialog_{question_uuid}"
                )
            ]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def make_completed_dialog_history_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершенного диалога с историей"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Посмотреть историю диалога",
                    callback_data="view_completed_dialog_history"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Задать новый вопрос",
                    callback_data="ask_new_question"
                ),
                InlineKeyboardButton(
                    text="📋 Мои вопросы",
                    callback_data="my_questions"
                )
            ],
            [
                InlineKeyboardButton(
    text="🔍 Поиск лекарств",
    web_app = WebAppInfo(url="https://spravka.novamedika.com/")
),
            ]
        ]
    )


def make_full_history_keyboard(question_uuid: str, can_clarify: bool = True, has_photo_request: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для полной истории консультации"""
    buttons = []

    # Основные действия
    if can_clarify:
        buttons.append([
            InlineKeyboardButton(
                text="✍️ Уточнить вопрос",
                callback_data=f"quick_clarify_{question_uuid}"
            )
        ])

    if has_photo_request:
        buttons.append([
            InlineKeyboardButton(
                text="📸 Отправить фото рецепта",
                callback_data=f"send_prescription_photo_{question_uuid}"
            )
        ])

    # Дополнительные действия
    buttons.append([
        InlineKeyboardButton(
            text="📋 Скопировать историю",
            callback_data=f"export_history_{question_uuid}"
        ),
        InlineKeyboardButton(
            text="✅ Завершить",
            callback_data=f"end_dialog_{question_uuid}"
        )
    ])

    # Навигация
    buttons.append([
        InlineKeyboardButton(
            text="🔙 К списку вопросов",
            callback_data="back_to_questions"
        ),
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def make_questions_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура для работы с вопросами"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Все мои вопросы",
                    callback_data="my_questions_callback"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Активные вопросы",
                    callback_data="filter_active"
                ),
                InlineKeyboardButton(
                    text="✅ Завершенные",
                    callback_data="filter_completed"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="questions_stats"
                ),
                InlineKeyboardButton(
                    text="📤 Экспорт всех",
                    callback_data="export_all_questions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск по вопросам",
                    callback_data="search_questions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В главное меню",
                    callback_data="back_to_main"
                )
            ]
        ]
    )
