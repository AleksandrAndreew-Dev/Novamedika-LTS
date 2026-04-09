"""QA handlers package — объединяет все роутеры Q&A бота."""

from aiogram import Router

from .commands import router as commands_router
from .dialog_callbacks import router as dialog_callbacks_router
from .dialog_handlers import router as dialog_handlers_router
from .photo_handlers import router as photo_handlers_router
from .user_handlers import router as user_handlers_router

# Главный роутер пакета
router = Router()

for sub_router in (
    commands_router,
    dialog_callbacks_router,
    dialog_handlers_router,
    photo_handlers_router,
    user_handlers_router,
):
    router.include_router(sub_router)
