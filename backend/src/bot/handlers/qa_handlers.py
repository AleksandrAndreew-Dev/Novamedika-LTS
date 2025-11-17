
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from typing import List
from datetime import timedelta

from db.qa_models import Question, Pharmacist, User
from bot.handlers.qa_states import QAStates
from utils.time_utils import get_utc_now_naive
import logging



logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("online"))
async def set_online(message: Message, db: AsyncSession):
    """Перевести фармацевта в онлайн"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(User.telegram_id == message.from_user.id)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            await message.answer("❌ Фармацевт не найден. Пройдите регистрацию /start")
            return

        # Обновляем статус всех фармацевтов пользователя
        for pharmacist in pharmacists:
            pharmacist.is_online = True
            pharmacist.last_seen = get_utc_now_naive()

        await db.commit()

        await message.answer("✅ Вы теперь онлайн и готовы принимать вопросы!")

    except Exception as e:
        logger.error(f"Error setting online status: {e}")
        await message.answer("❌ Ошибка при изменении статуса")

@router.message(Command("offline"))
async def set_offline(message: Message, db: AsyncSession):
    """Перевести фармацевта в офлайн"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(User.telegram_id == message.from_user.id)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            await message.answer("❌ Фармацевт не найден. Пройдите регистрацию /start")
            return

        # Обновляем статус всех фармацевтов пользователя
        for pharmacist in pharmacists:
            pharmacist.is_online = False
            pharmacist.last_seen = get_utc_now_naive()

        await db.commit()

        await message.answer("✅ Вы теперь офлайн и не будете получать новые уведомления")

    except Exception as e:
        logger.error(f"Error setting offline status: {e}")
        await message.answer("❌ Ошибка при изменении статуса")

@router.message(Command("status"))
async def get_status(message: Message, db: AsyncSession):
    """Показать статус фармацевта"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(User.telegram_id == message.from_user.id)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            await message.answer("❌ Фармацевт не найден. Пройдите регистрацию /start")
            return

        pharmacist = pharmacists[0]  # Берем первого

        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"

        await message.answer(
            f"📊 Ваш статус:\n\n"
            f"{status_text}\n"
            f"Сеть: {pharmacist.pharmacy_info.get('chain', 'Не указана')}\n"
            f"Аптека №: {pharmacist.pharmacy_info.get('number', 'Не указан')}\n"
            f"Роль: {pharmacist.pharmacy_info.get('role', 'Не указана')}\n"
            f"Последняя активность: {pharmacist.last_seen.strftime('%H:%M %d.%m.%Y')}"
        )

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.answer("❌ Ошибка при получении статуса")

# qa_handlers.py - ОБНОВЛЕННЫЙ ФРАГМЕНТ
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

        # Показываем количество онлайн фармацевтов
        online_threshold = get_utc_now_naive() - timedelta(minutes=5)
        result = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_online == True)
            .where(Pharmacist.last_seen >= online_threshold)
        )
        online_count = result.scalar() or 0

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions:
            # Обрезаем текст вопроса для кнопки
            question_preview = question.text[:100] + "..." if len(question.text) > 100 else question.text
            btn = InlineKeyboardButton(
                text=f"❓ {question_preview}",
                callback_data=f"answer_{question.uuid}"
            )
            keyboard.inline_keyboard.append([btn])

        status_text = f"\n👥 Фармацевтов онлайн: {online_count}" if online_count > 0 else "\n⚠️ Сейчас нет фармацевтов онлайн"

        await message.answer(
            f"Выберите вопрос для ответа:{status_text}\n\n"
            "💡 Нажмите на вопрос чтобы ответить на него",
            reply_markup=keyboard
        )
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

        # ИСПРАВЛЕННЫЙ ПОИСК: получаем ВСЕХ фармацевтов для пользователя
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(User.telegram_id == message.from_user.id)
            .where(Pharmacist.is_active == True)  # только активные
            .options(selectinload(Pharmacist.user))
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            await message.answer("❌ Фармацевт не найден. Пройдите регистрацию /start")
            await state.clear()
            return

        # Если несколько фармацевтов, берем первого активного
        pharmacist = pharmacists[0]

        # Обновляем время последней активности
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()

        # Если нужно дать выбор аптеки, можно добавить клавиатуру выбора
        if len(pharmacists) > 1:
            # Пока берем первого, но можно добавить выбор аптеки
            logger.info(f"User {message.from_user.id} has {len(pharmacists)} pharmacist profiles, using first active")

        # Используем внутреннюю функцию
        from bot.services.qa_service import answer_question_internal
        from db.qa_schemas import AnswerBase

        answer_data = AnswerBase(text=message.text)
        await answer_question_internal(question_id, answer_data, pharmacist, db)

        await message.answer("✅ Ответ успешно отправлен!")
        await state.clear()

    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        await message.answer("❌ Ошибка при отправке ответа")
        await state.clear()

# В этом файле определен только router, поэтому __all__ должен содержать только его
__all__ = ['router']

