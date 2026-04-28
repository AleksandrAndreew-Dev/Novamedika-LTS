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
    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")
    # URL для Pharmacist Dashboard (консультации)
    pharmacist_dashboard_url = os.getenv(
        "PHARMACIST_DASHBOARD_URL", 
        "https://pharmacist.spravka.novamedika.com"
    )
    
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
                    text="💼 Панель фармацевта",
                    web_app=WebAppInfo(url=pharmacist_dashboard_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Политика конфиденциальности",
                    callback_data="show_privacy_policy"
                )
            ],
        ],
    )


def get_user_inline_keyboard():
    """Inline-клавиатура пользователя"""
    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")
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
                    text="👨‍⚕️ Я фармацевт / Регистрация",
                    callback_data="i_am_pharmacist",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Политика конфиденциальности",
                    callback_data="show_privacy_policy"
                )
            ],
        ],
    )


def get_webapp_only_keyboard():
    """Reply-клавиатура только с WebApp (inline не поддерживает WebAppInfo)"""
    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🔍 Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Откройте поиск лекарств...",
    )
