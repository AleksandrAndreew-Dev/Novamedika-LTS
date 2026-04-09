"""Обработчики вопросов от пользователя (не фармацевта)."""

import logging

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.handlers.qa_states import UserQAStates

logger = logging.getLogger(__name__)

router = __import__('aiogram').Router()


@router.callback_query(F.data == "ask_new_question")
async def ask_new_question_callback(
    callback: CallbackQuery, state: FSMContext, is_pharmacist: bool
):
    """Начать новый вопрос после завершенного диалога"""
    if is_pharmacist:
        await callback.answer(
            "👨‍⚕️ Вы фармацевт. Используйте /questions для ответов.", show_alert=True
        )
        return

    await state.clear()
    await state.set_state(UserQAStates.waiting_for_question)

    await callback.message.answer(
        "📝 <b>ЗАДАТЬ НОВЫЙ ВОПРОС</b>\n\n"
        "Просто напишите ваш вопрос в чат:\n\n"
        "<i>Опишите вашу проблему подробно, чтобы фармацевт мог дать точный ответ.</i>\n\n"
        "💡 <b>Примеры вопросов:</b>\n"
        "• Что можно принимать от головной боли?\n"
        "• Нужна консультация по детским витаминам\n"
        "• Помогите подобрать аналоги лекарства\n\n"
        "Для отмены используйте /cancel",
        parse_mode="HTML",
    )
    await callback.answer()
