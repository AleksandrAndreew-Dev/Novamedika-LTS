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
        pharmacist_uuid: UUID фармацевта (опционально)
    
    Returns:
        URL с JWT токеном в query параметрах
    """
    # Создаем JWT токен с данными фармацевта
    # IMPORTANT: Backend expects 'sub' field for get_current_pharmacist dependency
    token_data = {
        "sub": pharmacist_uuid if pharmacist_uuid else str(telegram_id),  # Use 'sub' for pharmacist UUID
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