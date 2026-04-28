"""Команды пользователя: /ask, /my_questions, /done."""

import logging

from typing import Union, List

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.qa_models import User, Question, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers import get_user_inline_keyboard
from bot.keyboards.pagination_keyboard import make_questions_pagination_keyboard
from bot.handlers.dialog_management import complete_dialog_service
from src.utils.get_utils import get_all_pharmacist_questions
from src.utils.pharm_format_questions import format_pharmacist_questions_list

logger = logging.getLogger(__name__)

router = Router()


async def get_all_user_questions(
    db: AsyncSession, user: User, limit: int = 50
) -> List[Question]:
    """Получить все вопросы пользователя"""
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.user))
        .where(Question.user_id == user.uuid)
        .order_by(Question.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def format_questions_list(
    questions: List[Question], page: int = 0, per_page: int = 10
) -> str:
    """Форматировать список вопросов для отображения"""
    start_idx = page * per_page
    end_idx = start_idx + per_page

    message_text = f"📋 <b>ВАШИ ВОПРОСЫ</b>\n\n"

    if not questions:
        return (
            message_text
            + "📭 У вас пока нет вопросов.\n\nЗадайте первый вопрос, просто написав его в чат."
        )

    for i, question in enumerate(questions[start_idx:end_idx], start_idx + 1):
        status_icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "answered": "💬",
            "completed": "✅",
        }
        icon = status_icons.get(question.status, "❓")
        time_str = question.created_at.strftime("%d.%m.%Y %H:%M")
        question_preview = (
            question.text[:80] + "..." if len(question.text) > 80 else question.text
        )

        message_text += f"{icon} <b>Вопрос #{i}:</b>\n"
        message_text += f"📅 {time_str}\n"
        message_text += f"📝 {question_preview}\n"
        message_text += f"📊 Статус: {question.status.replace('_', ' ').title()}\n\n"

    total = len(questions)
    total_pages = (total + per_page - 1) // per_page

    if total_pages > 1:
        message_text += f"📄 Страница {page + 1} из {total_pages} "
        message_text += f"(всего {total} вопросов)\n\n"

    return message_text


@router.message(Command("ask"))
async def cmd_ask(message: Message):
    """Быстрая команда для вопроса"""
    await message.answer(
        "💬 <b>Напишите ваш вопрос:</b>\n\n"
        "Пример:\n"
        '<i>"Нужны витамины для ребенка 5 лет"</i>',
        parse_mode="HTML",
    )


@router.message(Command("my_questions"))
@router.callback_query(F.data == "my_questions_callback")
async def cmd_my_questions(
    update: Union[Message, CallbackQuery],
    db: AsyncSession | None = None,
    user: User | None = None,
    is_pharmacist: bool | None = None,
):
    """Показать все вопросы пользователя или фармацевта с пагинацией"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in cmd_my_questions")
        if isinstance(update, CallbackQuery):
            await update.answer("❌ Ошибка сервера", show_alert=True)
        else:
            await update.answer("❌ Ошибка сервера")
        return
        
    if isinstance(update, CallbackQuery):
        message = update.message
        is_callback = True
    else:
        message = update
        is_callback = False

    try:
        if is_pharmacist:
            result = await db.execute(
                select(Pharmacist).where(Pharmacist.user_id == user.uuid)
            )
            pharmacist = result.scalar_one_or_none()

            if not pharmacist:
                await message.answer("❌ Вы не найдены как фармацевт")
                if is_callback:
                    await update.answer()
                return

            questions = await get_all_pharmacist_questions(db, pharmacist, limit=50)
            page = 0
            header = "📋 <b>Ваши вопросы</b>\n\nВыберите вопрос для просмотра:\n\n"
            formatted = await format_pharmacist_questions_list(questions, page)
            message_text = header + formatted
            reply_markup = make_questions_pagination_keyboard(
                questions, page, is_pharmacist=True, pharmacist_id=str(pharmacist.uuid)
            )
        else:
            questions = await get_all_user_questions(db, user, limit=50)
            page = 0
            header = "📋 <b>Ваши вопросы</b>\n\nВыберите вопрос для просмотра:\n\n"
            formatted = await format_questions_list(questions, page)
            message_text = header + formatted
            reply_markup = make_questions_pagination_keyboard(questions, page)

        await message.answer(message_text, parse_mode="HTML", reply_markup=reply_markup)

        if is_callback:
            await update.answer()

    except Exception as e:
        logger.error(f"Error in cmd_my_questions: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении вопросов")


@router.message(Command("done"))
async def cmd_done(
    message: Message,
    state: FSMContext,
    is_pharmacist: bool | None = None,
    user: User | None = None,
    db: AsyncSession | None = None,
):
    """Завершение диалога через /done - теперь с обновлением БД"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in cmd_done")
        await message.answer("❌ Ошибка сервера")
        return
        
    logger.info(
        f"Command /done from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    current_state = await state.get_state()

    if current_state != UserQAStates.in_dialog:
        await message.answer("ℹ️ В данный момент у вас нет активного диалога.")
        return

    # Получаем UUID вопроса из состояния
    state_data = await state.get_data()
    question_uuid = state_data.get("active_dialog_question_id")

    if not question_uuid:
        await message.answer("❌ Не найден активный диалог.")
        await state.clear()
        return

    # Проверяем, что вопрос существует и принадлежит пользователю
    result = await db.execute(select(Question).where(Question.uuid == question_uuid))
    question = result.scalar_one_or_none()

    if not question or question.user_id != user.uuid:
        await message.answer("❌ Диалог не найден или недоступен.")
        await state.clear()
        return

    if question.status == "completed":
        await message.answer("✅ Эта консультация уже завершена.")
        await state.clear()
        return

    # Завершаем диалог через сервис
    success = await complete_dialog_service(
        question_uuid=question_uuid,
        db=db,
        initiator_type="user",
        initiator=user,
        message=message,
    )

    if success:
        await state.clear()
        await message.answer(
            "✅ <b>Диалог завершен</b>\n\n"
            "Фармацевт уведомлен.\n\n"
            "Если у вас есть еще вопросы, используйте /ask",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "❌ Произошла ошибка при завершении диалога. Попробуйте еще раз."
        )
