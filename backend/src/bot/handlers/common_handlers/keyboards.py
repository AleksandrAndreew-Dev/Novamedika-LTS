"""Фабрики клавиатур для бота."""

import os

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)


def get_reply_keyboard_with_webapp():
    """Клавиатура с WebApp для поиска лекарств"""
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
            [
                KeyboardButton(text="❓ Задать вопрос"),
                KeyboardButton(text="📋 Мои вопросы"),
            ],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите вопрос...",
    )


def get_pharmacist_keyboard():
    """Клавиатура для фармацевта"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Онлайн"), KeyboardButton(text="⚫ Офлайн")],
            [
                KeyboardButton(text="📋 Вопросы"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="🔍 Поиск лекарств")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def get_user_keyboard():
    """Клавиатура для пользователя"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❓ Задать вопрос"),
                KeyboardButton(text="📋 Мои вопросы"),
            ],
            [KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="🔍 Поиск лекарств")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите вопрос...",
    )
