from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
import uuid
from datetime import timedelta

from db.qa_models import User, Question, Pharmacist
from db.qa_schemas import QuestionCreate
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)
router = Router()


async def get_or_create_user(
    telegram_id: int, first_name: str, username: str, db: AsyncSession
) -> User:
    """Создать или найти пользователя - БЕЗ РЕГИСТРАЦИИ"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_id,
            first_name=first_name,
            telegram_username=username,
            user_type="customer",
        )
        db.add(user)
        await db.flush()

    return user


@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext, db: AsyncSession):
    """Команда для задания вопроса"""
    # Показываем количество онлайн фармацевтов
    online_threshold = get_utc_now_naive() - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(Pharmacist.uuid))
        .where(Pharmacist.is_online == True)
        .where(Pharmacist.last_seen >= online_threshold)
    )
    online_count = result.scalar() or 0

    status_text = (
        f"👥 Фармацевтов онлайн: {online_count}\n\n"
        if online_count > 0
        else "⏳ В настоящее время фармацевтов нет онлайн, но ваш вопрос будет сохранен\n\n"
    )

    await message.answer(
        f"{status_text}"
        "💊 Задайте ваш вопрос фармацевту:\n\n"
        "Просто напишите ваш вопрос и отправьте его. "
        "Фармацевты ответят вам в ближайшее время."
    )


@router.message(F.text & ~F.command)
async def handle_user_question(message: Message, db: AsyncSession):
    """Обработка вопросов от пользователей (только для пользователей)"""
    try:
        # ПРОВЕРЯЕМ, ЯВЛЯЕТСЯ ЛИ ПОЛЬЗОВАТЕЛЬ ФАРМАЦЕВТОМ
        from routers.pharmacist_auth import get_pharmacist_by_telegram_id
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        if pharmacist:
            # Если это фармацевт, игнорируем обычные сообщения
            logger.info(f"Pharmacist {pharmacist.uuid} sent message, ignoring as user question")
            return
        
        # Создаем или находим пользователя
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            db=db,
        )

        # Создаем вопрос
        question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=message.text,
            status="pending",
            category="general",
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        # Уведомляем фармацевтов
        from bot.services.notification_service import (
            notify_pharmacists_about_new_question,
        )

        await notify_pharmacists_about_new_question(question, db)

        await message.answer(
            "✅ Ваш вопрос принят! Ожидайте ответа от фармацевта.\n\n"
            "Вы получите уведомление, когда на ваш вопрос ответят."
        )

        logger.info(f"New question from user {user.uuid}: {message.text[:100]}...")

    except Exception as e:
        logger.error(f"Error processing user question: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке вопроса. Попробуйте позже."
        )


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
            await message.answer(
                "📭 У вас пока нет вопросов. Задайте вопрос с помощью команды /ask"
            )
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


@router.message(Command("help"))
async def user_help(message: Message, db: AsyncSession):
    """Справка для пользователей"""
    help_text = (
        "💊 Бот вопрос-ответ Novamedika\n\n"
        "📋 Доступные команды:\n\n"
        "❓ Задать вопрос:\n"
        "/ask - Задать вопрос фармацевту\n"
        "/my_questions - Мои вопросы и ответы\n\n"
        "ℹ️ Справка:\n"
        "/help - Эта справка\n\n"
        "Просто напишите ваш вопрос и отправьте его - фармацевты ответят вам в ближайшее время!"
    )
    await message.answer(help_text)
