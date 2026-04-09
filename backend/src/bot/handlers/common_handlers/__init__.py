"""Common handlers package — объединяет все роутеры общего назначения."""

from aiogram import Router

from .keyboards import (
    get_pharmacist_inline_keyboard,
    get_user_inline_keyboard,
    get_webapp_only_keyboard,
)
from .commands import router as commands_router
from .callbacks import router as callbacks_router
from .button_fallbacks import router as button_fallbacks_router

# Главный роутер пакета
router = Router()

# button_fallbacks ДО commands, чтобы перехватить текст кнопок
# до того как unknown_command их обработает
for sub_router in (button_fallbacks_router, commands_router, callbacks_router):
    router.include_router(sub_router)
