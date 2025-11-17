# bot/handlers/qa_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from typing import List

from db.qa_models import Question, Pharmacist
from db.qa_schemas import QuestionCreate
from bot.handlers.qa_states import QAStates

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("questions"))
async def cmd_questions(message: Message, state: FSMContext, db: AsyncSession):
    """Показать вопросы, ожидающие ответа"""
    try:
        # Получаем незавершенные вопросы
        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.desc())
            .limit(10)
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer("📭 Нет вопросов, ожидающих ответа")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions:
            text = f"❓ Вопрос #{question.uuid}\n{question.text[:100]}..."
            btn = InlineKeyboardButton(
                text=f"Ответить на вопрос #{question.uuid}",
                callback_data=f"answer_{question.uuid}"
            )
            keyboard.inline_keyboard.append([btn])
            await message.answer(text)

        await message.answer("Выберите вопрос для ответа:", reply_markup=keyboard)
        await state.set_state(QAStates.viewing_questions)

    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")

@router.callback_query(F.data.startswith("answer_"))
async def process_answer_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Обработка выбора вопроса для ответа"""
    question_id = callback.data.replace("answer_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_id)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("Вопрос не найден")
            return

        await state.update_data(selected_question_id=question_id)
        await callback.message.answer(
            f"✍️ Введите ответ на вопрос:\n\n{question.text}"
        )
        await state.set_state(QAStates.waiting_for_answer)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error processing answer callback: {e}")
        await callback.answer("Ошибка при выборе вопроса")

@router.message(QAStates.waiting_for_answer)
async def process_answer_text(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка текста ответа"""
    try:
        data = await state.get_data()
        question_id = data.get('selected_question_id')

        if not question_id:
            await message.answer("❌ Ошибка: вопрос не выбран")
            await state.clear()
            return

        # Находим фармацевта
        result = await db.execute(
            select(Pharmacist)
            .join(Pharmacist.user)
            .where(Pharmacist.user.telegram_id == message.from_user.id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist:
            await message.answer("❌ Фармацевт не найден. Пройдите регистрацию /start")
            await state.clear()
            return

        # Отправляем ответ через API
        from routers.qa import answer_question
        from db.qa_schemas import AnswerBase

        answer_data = AnswerBase(text=message.text)
        await answer_question(question_id, answer_data, pharmacist, db)

        await message.answer("✅ Ответ успешно отправлен!")
        await state.clear()

    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        await message.answer("❌ Ошибка при отправке ответа")
        await state.clear()
