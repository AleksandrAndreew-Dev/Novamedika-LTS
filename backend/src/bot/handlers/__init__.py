from .common_handlers import router as common_router
from .registration import router as registration_router
from .user_questions import router as user_questions_router
from .qa_handlers import router as qa_handlers_router

__all__ = [
    'common_router',
    'registration_router',
    'user_questions_router',
    'qa_handlers_router'
]
