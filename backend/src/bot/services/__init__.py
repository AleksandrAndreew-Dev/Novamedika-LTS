from .notification_service import (
    notify_pharmacists_about_new_question,
    notify_about_clarification,
    get_online_pharmacists
)

from .assignment_service import QuestionAssignmentService  # Добавьте эту строку
from .qa_service import answer_question_internal  # Если используется

__all__ = [
    'notify_pharmacists_about_new_question',
    'notify_about_clarification',
    'get_online_pharmacists',
    'QuestionAssignmentService',  # Добавьте эту строку
    'answer_question_internal',   # Если используется
]
