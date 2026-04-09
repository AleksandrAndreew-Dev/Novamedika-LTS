from typing import List
from db.qa_models import Question
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def make_questions_pagination_keyboard(
    questions: List[Question],
    page: int = 0,
    per_page: int = 10,
    include_back: bool = True,
    is_pharmacist: bool = False,
    pharmacist_id: str = None
) -> InlineKeyboardMarkup:
    """Создать клавиатуру пагинации для списка вопросов"""
    total = len(questions)
    total_pages = (total + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total)

    keyboard = []

    # Кнопки для вопросов на текущей странице
    for i, question in enumerate(questions[start_idx:end_idx], start_idx):
        question_preview = (
            question.text[:40] + "..." if len(question.text) > 40 else question.text
        )

        if is_pharmacist:
            # Для фармацевта - кнопка просмотра диалога
            callback_data = f"view_dialog_{question.uuid}"
        else:
            # Для пользователя - кнопка просмотра истории
            callback_data = f"view_full_history_{question.uuid}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📋 Вопрос #{i+1}: {question_preview}",
                    callback_data=callback_data,
                )
            ]
        )

    # Кнопки пагинации
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"questions_page_{page-1}"
            )
        )

    pagination_buttons.append(
        InlineKeyboardButton(
            text=f"{page+1}/{total_pages}", callback_data="current_page"
        )
    )

    if page < total_pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", callback_data=f"questions_page_{page+1}"
            )
        )

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    if not is_pharmacist:
        # Кнопки фильтрации только для пользователей
        filter_buttons = []
        filter_buttons.append(
            InlineKeyboardButton(text="🎯 Активные", callback_data="filter_active")
        )
        filter_buttons.append(
            InlineKeyboardButton(text="✅ Завершенные", callback_data="filter_completed")
        )
        keyboard.append(filter_buttons)

    # Кнопка возврата
    if include_back:


        if is_pharmacist:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text="🔙 В панель фармацевта",
                        callback_data="back_to_pharmacist_main"
                    )
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text="🔙 В главное меню", callback_data="back_to_main"
                    )
                ]
            )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
