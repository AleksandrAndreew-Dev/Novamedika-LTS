# bot/handlers/user_questions.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid

from db.qa_models import User, Question
from db.qa_schemas import QuestionCreate

logger = logging.getLogger(__name__)
router = Router()

async def get_or_create_user(telegram_id: int, first_name: str, username: str, db: AsyncSession) -> User:
    """Создать или найти пользователя"""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_id,
            first_name=first_name,
            telegram_username=username,
            user_type="customer"
        )
        db.add(user)
        await db.flush()

    return user

@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Команда для задания вопроса"""
    await message.answer(
        "💊 Задайте ваш вопрос фармацевту:\n\n"
        "Просто напишите ваш вопрос и отправьте его. "
        "Фармацевты ответят вам в ближайшее время."
    )

@router.message(F.text & ~F.command)
async def handle_user_question(message: Message, db: AsyncSession):
    """Обработка вопросов от пользователей (без регистрации)"""
    try:
        # Создаем или находим пользователя
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            db=db
        )

        # Создаем вопрос
        question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=message.text,
            status="pending",
            category="general"
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        # Уведомляем фармацевтов
        from bot.services.notification_service import notify_pharmacists_about_new_question
        await notify_pharmacists_about_new_question(question, db)

        await message.answer(
            "✅ Ваш вопрос принят! Ожидайте ответа от фармацевта.\n\n"
            "Вы получите уведомление, когда на ваш вопрос ответят."
        )

        logger.info(f"New question from user {user.uuid}: {message.text[:100]}...")

    except Exception as e:
        logger.error(f"Error processing user question: {e}")
        await message.answer("❌ Произошла ошибка при отправке вопроса. Попробуйте позже.")

@router.message(Command("my_questions"))
async def cmd_my_questions(message: Message, db: AsyncSession):
    """Показать вопросы пользователя и ответы на них"""
    try:
        result = await db.execute(
            select(Question)
            .join(User)
            .where(User.telegram_id == message.from_user.id)
            .order_by(Question.created_at.desc())
            .limit(10)
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer("📭 У вас пока нет вопросов. Задайте вопрос с помощью команды /ask")
            return

        for question in questions:
            status_emoji = "✅" if question.status == "answered" else "⏳"
            text = f"{status_emoji} Вопрос: {question.text[:200]}...\n"
            text += f"Статус: {question.status}\n"
            text += f"Дата: {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"

            if question.answers:
                text += f"\n💊 Ответ фармацевта: {question.answers[0].text[:200]}..."

            await message.answer(text)

    except Exception as e:
        logger.error(f"Error getting user questions: {e}")
        await message.answer("❌ Ошибка при получении ваших вопросов")
