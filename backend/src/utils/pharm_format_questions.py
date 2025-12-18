from typing import List
from db.qa_models import Question




async def format_pharmacist_questions_list(
    questions: List[Question], page: int = 0, per_page: int = 10
) -> str:
    """Форматировать список вопросов фармацевта для отображения"""
    start_idx = page * per_page
    end_idx = start_idx + per_page

    message_text = f"📋 <b>ВАШИ ВОПРОСЫ (Фармацевт)</b>\n\n"

    if not questions:
        return (
            message_text
            + "📭 У вас пока нет взятых вопросов.\n\nИспользуйте /questions для просмотра доступных вопросов."
        )

    # Показываем вопросы на текущей странице
    for i, question in enumerate(questions[start_idx:end_idx], start_idx + 1):
        status_icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "answered": "💬",
            "completed": "✅",
        }
        icon = status_icons.get(question.status, "❓")
        time_str = question.created_at.strftime("%d.%m.%Y %H:%M")

        # Обрезаем длинный текст
        question_preview = question.text[:80]
        if len(question.text) > 80:
            question_preview += "..."

        message_text += f"{icon} <b>Вопрос #{i}:</b>\n"
        message_text += f"📅 {time_str}\n"
        message_text += f"📝 {question_preview}\n"
        message_text += f"📊 Статус: {question.status.replace('_', ' ').title()}\n\n"

    # Информация о пагинации
    total = len(questions)
    total_pages = (total + per_page - 1) // per_page

    if total_pages > 1:
        message_text += f"📄 Страница {page + 1} из {total_pages} "
        message_text += f"(всего {total} вопросов)\n\n"

    return message_text
