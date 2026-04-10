"""Fallback-хендлеры для текста reply-кнопок.

Перенаправляют на callback-обработчики, если пользователь отправил
текст кнопки (🟢 Онлайн, 📋 Вопросы и т.д.) как обычное сообщение.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.qa_models import User, Question
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers.keyboards import (
    get_pharmacist_inline_keyboard,
    get_user_inline_keyboard,
)
from bot.handlers.user_question_handlers.commands import cmd_my_questions
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


# ---------- Фармацевт ----------

PHARMACIST_BUTTONS = {
    "🟢 Онлайн": "go_online",
    "⚫ Офлайн": "go_offline",
    "📋 Вопросы": "view_questions",
    "📊 Статистика": "questions_stats",
    "📜 История": "my_questions_from_completed",
    "❓ Помощь": "pharmacist_help",
}


@router.message(F.text.in_(PHARMACIST_BUTTONS.keys()))
async def pharmacist_button_fallback(
    message: Message,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object,
    user: User,
    state: FSMContext,
):
    """Перенаправляет текст кнопки фармацевта на соответствующий callback"""
    if not is_pharmacist:
        return

    action = PHARMACIST_BUTTONS[message.text]

    if action == "go_online":
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        await message.answer(
            "🟢 <b>Вы теперь онлайн!</b>\n\n"
            "Вы будете получать уведомления о новых вопросах.",
            parse_mode="HTML",
            reply_markup=get_pharmacist_inline_keyboard(),
        )

    elif action == "go_offline":
        pharmacist.is_online = False
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        await message.answer(
            "🔴 <b>Вы теперь офлайн.</b>\n\n"
            "Вы не будете получать уведомления о новых вопросах.",
            parse_mode="HTML",
            reply_markup=get_pharmacist_inline_keyboard(),
        )

    elif action == "view_questions":
        await cmd_my_questions(message, db, user, is_pharmacist)

    elif action == "questions_stats":
        await message.answer("📊 Эта функция доступна только пользователям")

    elif action == "my_questions_from_completed":
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid, Question.status == "completed")
            .order_by(Question.created_at.desc())
            .limit(10)
        )
        questions = result.scalars().all()
        if not questions:
            await message.answer("📭 У вас пока нет завершённых вопросов")
            return
        text = "📜 <b>История вопросов:</b>\n\n"
        for i, q in enumerate(questions, 1):
            preview = q.text[:80] + "..." if len(q.text) > 80 else q.text
            text += f"{i}. {preview}\n"
        await message.answer(text, parse_mode="HTML")

    elif action == "pharmacist_help":
        await message.answer(
            "👨‍⚕️ <b>Как отвечать на вопросы?</b>\n\n"
            "1. Нажмите «🟢 Перейти в онлайн»\n"
            "2. Как придёт уведомление — нажмите «💬 Ответить»\n"
            "3. Напишите ответ пользователю",
            parse_mode="HTML",
            reply_markup=get_pharmacist_inline_keyboard(),
        )


# ---------- Пользователь ----------

USER_BUTTONS = {
    "❓ Задать вопрос": "ask_question",
    "📋 Мои вопросы": "my_questions",
    "📜 История": "my_questions_from_completed",
    "❓ Помощь": "user_help",
    "👨‍⚕️ Я фармацевт / Регистрация": "i_am_pharmacist",
}


@router.message(F.text.in_(USER_BUTTONS.keys()))
async def user_button_fallback(
    message: Message,
    db: AsyncSession,
    is_pharmacist: bool,
    user: User,
    state: FSMContext,
):
    """Перенаправляет текст кнопки пользователя на соответствующий callback"""
    if is_pharmacist:
        return

    action = USER_BUTTONS[message.text]

    if action == "ask_question":
        await state.set_state(UserQAStates.waiting_for_question)
        await message.answer(
            "📝 <b>Напишите ваш вопрос:</b>\n\n"
            "Опишите вашу проблему подробно.\n\n"
            "Для отмены: /cancel",
            parse_mode="HTML",
        )

    elif action == "my_questions":
        await cmd_my_questions(message, db, user, is_pharmacist)

    elif action == "my_questions_from_completed":
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid, Question.status == "completed")
            .order_by(Question.created_at.desc())
            .limit(10)
        )
        questions = result.scalars().all()
        if not questions:
            await message.answer("📭 У вас пока нет завершённых вопросов")
            return
        text = "📜 <b>История вопросов:</b>\n\n"
        for i, q in enumerate(questions, 1):
            preview = q.text[:80] + "..." if len(q.text) > 80 else q.text
            text += f"{i}. {preview}\n"
        await message.answer(text, parse_mode="HTML")

    elif action == "user_help":
        await message.answer(
            "👋 <b>Помощь для пользователей</b>\n\n"
            "1. Просто напишите вопрос в чат\n"
            "2. Фармацевт ответит в ближайшее время\n"
            "3. После ответа вы увидите кнопки для уточнения и завершения",
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )

    elif action == "i_am_pharmacist":
        await message.answer(
            "👨‍⚕️ <b>Регистрация фармацевта</b>\n\n"
            "Для регистрации обратитесь к администратору.\n\n"
            "Или нажмите кнопку «Регистрация» ниже.",
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )
