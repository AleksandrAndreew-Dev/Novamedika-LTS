from .common_handlers import router as common_router
from .registration import router as registration_router, RegistrationStates
from .user_question_handlers import (
    router as user_questions_router,
    get_all_user_questions,
    format_questions_list,
)
from .qa_handlers import router as qa_handlers_router
from bot.middleware.role_middleware import RoleMiddleware
from .clarify_handlers import router as clarify_router
from .dialog_management import router as dialog_management_router

# direct_questions — теперь только утилиты, без роутера
from .direct_questions import try_create_question

__all__ = [
    "common_router",
    "user_questions_router",
    "registration_router",
    "qa_handlers_router",
    "RoleMiddleware",
    "clarify_router",
    "RegistrationStates",
    "dialog_management_router",
    "get_all_user_questions",
    "format_questions_list",
    "try_create_question",
]
