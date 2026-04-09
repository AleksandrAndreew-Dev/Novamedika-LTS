"""Common handlers package — объединяет все роутеры общего назначения."""

from aiogram import Router

from .keyboards import (
    get_reply_keyboard_with_webapp,
    get_pharmacist_keyboard,
    get_user_keyboard,
)
from .commands import router as commands_router
from .callbacks import router as callbacks_router

# Главный роутер пакета
router = Router()

for sub_router in (commands_router, callbacks_router):
    router.include_router(sub_router)
