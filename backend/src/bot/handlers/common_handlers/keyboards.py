"""Фабрики клавиатур для бота."""

import os

from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    WebAppInfo,
)


def get_pharmacist_webapp_url() -> str:
    """Генерирует URL для WebApp панели фармацевта

    Telegram WebApp передаст initData автоматически через SDK.
    Backend валидирует initData и выдаст JWT токен.

    Returns:
        URL без query параметров (Telegram добавит initData в hash)
    """
    # Базовый URL - используем path-based routing вместо subdomain
    base_url = os.getenv(
        "PHARMACIST_DASHBOARD_URL", "https://spravka.novamedika.com/pharmacist"
    )

    # НЕ добавляем query параметры - Telegram их удалит!
    # Вместо этого фронтенд использует window.Telegram.WebApp.initData
    return base_url


def get_pharmacist_inline_keyboard_with_token(
    telegram_id: int, pharmacist_uuid: str | None = None
):
    """Inline-клавиатура фармацевта с WebApp URL (без токена в URL)

    Args:
        telegram_id: Telegram ID фармацевта (не используется, оставлен для совместимости)
        pharmacist_uuid: UUID фармацевта (не используется, оставлен для совместимости)
    """
    # Получаем чистый URL без токена
    pharmacist_dashboard_url = get_pharmacist_webapp_url()

    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f7e2 Онлайн", callback_data="go_online"
                ),
                InlineKeyboardButton(text="\u26ab Офлайн", callback_data="go_offline"),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4cb Вопросы", callback_data="view_questions"
                ),
                InlineKeyboardButton(
                    text="\U0001f4ca Статистика", callback_data="questions_stats"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4dc История",
                    callback_data="my_questions_from_completed",
                ),
                InlineKeyboardButton(
                    text="\u2753 Помощь", callback_data="pharmacist_help"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4bc Панель фармацевта",
                    web_app=WebAppInfo(url=pharmacist_dashboard_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f50d Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
        ]
    )


def get_pharmacist_inline_keyboard():
    """Inline-клавиатура фармацевта (без токена)"""
    return get_pharmacist_inline_keyboard_with_token(0, None)


def get_user_inline_keyboard():
    """Inline-клавиатура пользователя"""
    webapp_url = os.getenv("FRONTEND_URL", "https://spravka.novamedika.com")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u2753 Задать вопрос", callback_data="ask_question"
                ),
                InlineKeyboardButton(
                    text="\U0001f4cb Мои вопросы", callback_data="my_questions"
                ),
            ],
            [
                InlineKeyboardButton(text="\u2753 Помощь", callback_data="user_help"),
                InlineKeyboardButton(
                    text="\U0001f4dc История",
                    callback_data="my_questions_from_completed",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👨‍⚕️ Я фармацевт / Регистрация",
                    callback_data="i_am_pharmacist",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4ac Чат с фармацевтом",
                    web_app=WebAppInfo(url=f"{webapp_url}/chat/new"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f50d Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f512 Политика конфиденциальности",
                    callback_data="show_privacy_policy",
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
                    text="\U0001f4ac Чат с фармацевтом",
                    web_app=WebAppInfo(url=f"{webapp_url}/chat/new"),
                )
            ],
            [
                KeyboardButton(
                    text="\U0001f50d Поиск лекарств",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
        ],
        resize_keyboard=True,
    )
