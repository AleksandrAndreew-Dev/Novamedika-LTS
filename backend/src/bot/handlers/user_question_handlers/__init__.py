"""User question handlers package — объединяет все роутеры вопросов пользователя."""

from aiogram import Router

from .commands import router as commands_router
from .question_callbacks import router as question_callbacks_router
from .message_handlers import router as message_handlers_router
from .photo_handlers import router as photo_handlers_router

# Экспортируем вспомогательные функции из commands
from .commands import get_all_user_questions, format_questions_list

# Главный роутер пакета
router = Router()

for sub_router in (
    commands_router,
    question_callbacks_router,
    message_handlers_router,
    photo_handlers_router,
):
    router.include_router(sub_router)
