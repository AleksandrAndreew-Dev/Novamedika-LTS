from .common_handlers import router as common_router
from .registration import router as registration_router
from .user_questions import router as user_questions_router
from .qa_handlers import router as qa_handlers_router
from bot.middleware.role_middleware import RoleMiddleware
from .direct_questions import router as direct_questions_router

__all__ = [
    "direct_questions_router",
    "common_router",
    "user_questions_router",
    "registration_router",
    "qa_handlers_router",
    "RoleMiddleware",
]
