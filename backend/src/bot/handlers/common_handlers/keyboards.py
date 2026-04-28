"""Фабрики клавиатур для бота."""

import os
from datetime import timedelta
from urllib.parse import urlencode

from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    WebAppInfo,
)

from auth.auth import create_access_token


def generate_pharmacist_webapp_url(telegram_id: int, pharmacist_uuid: str | None = None) -> str:
    """Генерирует URL для WebApp с JWT токеном
    
    Args:
        telegram_id: Telegram ID фармацевта
        pharmacist_uuid: UUID фармацевта (обязательно для корректной работы)
    
    Returns:
        URL с JWT токеном в query параметрах
        
    Raises:
        ValueError: Если pharmacist_uuid не предоставлен
    """
    if not pharmacist_uuid:
        raise ValueError("pharmacist_uuid is required for WebApp authentication")
    
    # Создаем JWT токен с данными фармацевта
    # IMPORTANT: Backend expects 'sub' field containing pharmacist UUID for get_current_pharmacist dependency
    token_data = {
        "sub": pharmacist_uuid,  # Must be pharmacist UUID, not telegram_id
        "telegram_id": telegram_id,
        "role": "pharmacist",
        "type": "access",  # Mark as access token type
    }
    
    access_token = create_access_token(data=token_data)
    
    # Базовый URL
    base_url = os.getenv(
        "PHARMACIST_DASHBOARD_URL", 
        "https://pharmacist.spravka.novamedika.com"
    )
    
    # Добавляем токен как query параметр
    params = {"token": access_token}
    query_string = urlencode(params)
    
    return f"{base_url}?{query_string}"


def get_pharmacist_inline_keyboard_with_token(telegram_id: int, pharmacist_uuid: str | None = None):
    """Inline-клавиатура фармацевта с JWT токеном в WebApp URL
    
    Args:
        telegram_id: Telegram ID фармацевта
        pharmacist_uuid: UUID фармацевта (обязательно)
    """
    if not pharmacist_uuid:
        # Fallback to non-token keyboard if pharmacist_uuid is missing (should not happen in normal flow)
        return get_pharmacist_inline_keyboard()
        
    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")
    # Генерируем URL с токеном
    pharmacist_dashboard_url = generate_pharmacist_webapp_url(telegram_id, pharmacist_uuid)
    
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


def get_pharmacist_inline_keyboard():
    """Inline-клавиатура фармацевта (без токена - для обратной совместимости)"""
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
            ]
        ],
        resize_keyboard=True,
    )