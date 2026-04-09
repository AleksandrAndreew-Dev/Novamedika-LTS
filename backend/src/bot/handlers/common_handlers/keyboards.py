"""Фабрики клавиатур для бота."""

import os

from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    WebAppInfo,
)


def get_pharmacist_inline_keyboard():
    """Inline-клавиатура фармацевта"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Онлайн", callback_data="go_online"),
                InlineKeyboardButton(text="⚫ Офлайн", callback_data="go_offline"),
            ],
            [
                InlineKeyboardButton(text="📋 Вопросы", callback_data="view_questions"),
                InlineKeyboardButton(
                    text="📊 Статистика", callback_data="questions_stats"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 История", callback_data="my_questions_from_completed"
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="pharmacist_help"),
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(
                        url=os.getenv("VITE_API_URL", "https://spravka.novamedika.com")
                    ),
                )
            ],
        ],
    )


def get_user_inline_keyboard():
    """Inline-клавиатура пользователя"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❓ Задать вопрос", callback_data="ask_question"
                ),
                InlineKeyboardButton(
                    text="📋 Мои вопросы", callback_data="my_questions"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 История", callback_data="my_questions_from_completed"
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="user_help"),
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(
                        url=os.getenv("VITE_API_URL", "https://spravka.novamedika.com")
                    ),
                )
            ],
        ],
    )


def get_webapp_only_keyboard():
    """Reply-клавиатура только с WebApp (inline не поддерживает WebAppInfo)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(
                        url=os.getenv("VITE_API_URL", "https://spravka.novamedika.com")
                    ),
                )
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Откройте поиск лекарств...",
    )
