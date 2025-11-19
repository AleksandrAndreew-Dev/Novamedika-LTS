
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import logging
import uuid
from datetime import timedelta

from db.qa_models import User, Question, Pharmacist, Answer
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)
router = Router()

# Состояния для диалога
from bot.handlers.qa_states import UserQAStates

async def get_or_create_user(
    telegram_id: int, first_name: str, username: str, db: AsyncSession
) -> User:
    """Создать или найти пользователя"""
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

async def update_question_with_additional_text(question_id: str, additional_text: str, db: AsyncSession):
    """Обновить вопрос дополнительным текстом"""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if question:
            # Добавляем текст к существующему вопросу
            question.text += f"\n\n[Дополнение]: {additional_text}"
            await db.commit()
            logger.info(f"Question {question_id} updated with additional text")

    except Exception as e:
        logger.error(f"Error updating question with additional text: {e}")
        raise


# В user_questions.py - для пользователей
@router.message(Command("help"))
async def user_help(message: Message, db: AsyncSession, is_pharmacist: bool):
    if is_pharmacist:
        return  # Пропускаем для фармацевтов
    await show_customer_help(message, db)

# В qa_handlers.py - для фармацевтов
@router.message(Command("help"))
async def pharmacist_help(message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist):
    if not is_pharmacist:
        return  # Пропускаем для пользователей
    await show_pharmacist_help(message, db)

@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Начать диалог с вопросом"""
    # Используем is_pharmacist из middleware
    if is_pharmacist:
        await message.answer("ℹ️ Вы зарегистрированы как фармацевт. Используйте команды /questions для ответов на вопросы.")
        return

    # Очищаем предыдущее состояние
    await state.clear()

    # Проверяем, не находится ли пользователь уже в диалоге
    current_state = await state.get_state()
    if current_state == UserQAStates.in_dialog:
        data = await state.get_data()
        question_id = data.get('current_question_id')
        if question_id:
            await message.answer("⚠️ У вас уже есть активный вопрос. Завершите его с помощью /done прежде чем задавать новый.")
            return

    # Показываем количество онлайн фармацевтов
    online_threshold = get_utc_now_naive() - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(Pharmacist.uuid))
        .where(Pharmacist.is_online == True)
        .where(Pharmacist.last_seen >= online_threshold)
    )
    online_count = result.scalar() or 0

    if online_count > 0:
        status_text = f"👥 Фармацевтов онлайн: {online_count}\n💬 Ваш вопрос будет обработан в ближайшее время\n\n"
    else:
        total_result = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_active == True)
        )
        total_pharmacists = total_result.scalar() or 0
        status_text = f"⏳ Сейчас нет фармацевтов онлайн (всего в системе: {total_pharmacists})\n📝 Ваш вопрос будет сохранен\n\n"

    await message.answer(
        f"{status_text}"
        "💊 Задайте ваш вопрос фармацевту:\n\n"
        "Просто напишите ваш вопрос и отправьте его. "
        "Фармацевты ответят вам в ближайшее время.\n\n"
        "❌ Чтобы отменить, используйте /cancel\n"
        "✅ Чтобы завершить вопрос, используйте /done"
    )
    await state.set_state(UserQAStates.waiting_for_question)

@router.message(Command("done"))
async def cmd_done_user(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Завершение вопроса для пользователей"""
    if is_pharmacist:
        return

    current_state = await state.get_state()

    if current_state == UserQAStates.in_dialog:
        data = await state.get_data()
        question_id = data.get('current_question_id')

        if question_id:
            try:
                result = await db.execute(
                    select(Question).where(Question.uuid == uuid.UUID(question_id))
                )
                question = result.scalar_one_or_none()
                if question:
                    # Добавляем пометку, что пользователь завершил диалог
                    question.context_data = question.context_data or {}
                    question.context_data["user_completed"] = True
                    question.context_data["completed_at"] = get_utc_now_naive().isoformat()
                    await db.commit()
                    logger.info(f"User completed question {question_id}")
            except Exception as e:
                logger.error(f"Error updating question completion: {e}")

    await state.clear()
    await message.answer(
        "✅ Диалог завершен. Если у вас появится новый вопрос, используйте /ask\n\n"
        "📋 Чтобы посмотреть историю вопросов, используйте /my_questions"
    )

@router.message(Command("my_questions"))
async def cmd_my_questions(message: Message, db: AsyncSession, is_pharmacist: bool):
    """Показать вопросы пользователя и ответы на них"""
    try:
        from sqlalchemy.orm import selectinload

        if is_pharmacist:
            await message.answer("ℹ️ Вы фармацевт. Используйте /questions для просмотра вопросов.")
            return

        result = await db.execute(
            select(Question)
            .join(User)
            .where(User.telegram_id == message.from_user.id)
            .options(selectinload(Question.answers))
            .order_by(Question.created_at.desc())
            .limit(10)
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer("📭 У вас пока нет вопросов. Задайте вопрос с помощью команды /ask")
            return

        for question in questions:
            status_emoji = "✅" if question.status == "answered" else "⏳"
            status_text = "отвечен" if question.status == "answered" else "ожидает ответа"

            text = f"{status_emoji} Вопрос ({status_text}):\n{question.text}\n"
            text += f"📅 Дата: {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"

            if question.answers:
                if len(question.answers) == 1:
                    text += f"\n💊 Ответ фармацевта:\n{question.answers[0].text}\n"
                    text += f"📅 Ответ дан: {question.answers[0].created_at.strftime('%d.%m.%Y %H:%M')}"
                else:
                    text += f"\n💊 Ответы фармацевтов ({len(question.answers)}):\n"
                    for i, answer in enumerate(question.answers, 1):
                        text += f"\n{i}. {answer.text}\n"
                        text += f"📅 Ответ дан: {answer.created_at.strftime('%d.%m.%Y %H:%M')}\n"

            # Разделяем длинные сообщения
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    await message.answer(part)
            else:
                await message.answer(text)

    except Exception as e:
        logger.error(f"Error getting user questions: {e}")
        await message.answer("❌ Ошибка при получении ваших вопросов")

@router.message(UserQAStates.waiting_for_question)
async def process_user_question(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Обработка вопроса пользователя"""
    if is_pharmacist:
        await message.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.")
        return

    try:
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
        from bot.services.notification_service import notify_pharmacists_about_new_question
        await notify_pharmacists_about_new_question(question, db)

        # Сохраняем ID вопрос для продолжения диалога
        await state.update_data(current_question_id=str(question.uuid))

        await message.answer(
            "✅ Ваш вопрос принят! Ожидайте ответа от фармацевта.\n\n"
            "Вы получите уведомление, когда на ваш вопрос ответят.\n"
            "Можете продолжать писать сообщения - они добавятся к этому же вопросу.\n\n"
            "✅ Чтобы завершить вопрос, используйте /done\n"
            "❌ Чтобы отменить, используйте /cancel"
        )

        # Переходим в состояние диалога
        await state.set_state(UserQAStates.in_dialog)
        logger.info(f"New question from user {user.uuid}: {message.text[:100]}...")

    except Exception as e:
        logger.error(f"Error processing user question: {e}")
        await message.answer("❌ Произошла ошибка при отправке вопроса. Попробуйте позже.")
        await state.clear()

@router.message(UserQAStates.in_dialog)
async def process_dialog_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist
):
    if is_pharmacist:
        return

    # Пропускаем команды для обработки другими хендлерами
    if message.text and message.text.startswith('/'):
        return

    data = await state.get_data()
    question_id = data.get('current_question_id')

    if not question_id:
        await message.answer("❌ Активный вопрос не найден. Используйте /ask для нового вопроса.")
        await state.clear()
        return

    # Обновить вопрос дополнительным сообщением
    await update_question_with_additional_text(question_id, message.text, db)
    await message.answer("✅ Сообщение добавлено к вопросу...")

@router.message(F.text & ~F.command)
async def handle_user_message(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Обработка обычных сообщений с улучшенным приветствием"""
    try:
        if is_pharmacist:
            logger.info(f"Pharmacist sent message, ignoring as user question")
            return

        # Проверяем состояние
        current_state = await state.get_state()

        if current_state == UserQAStates.in_dialog:
            await process_dialog_message(message, state, db, is_pharmacist)
        elif current_state == UserQAStates.waiting_for_question:
            await process_user_question(message, state, db, is_pharmacist)
        else:
            # ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ
            online_threshold = get_utc_now_naive() - timedelta(minutes=5)
            result = await db.execute(
                select(func.count(Pharmacist.uuid))
                .where(Pharmacist.is_online == True)
                .where(Pharmacist.last_seen >= online_threshold)
            )
            online_count = result.scalar() or 0

            welcome_text = (
                "👋 Привет!\n\n"
                "💊 **Добро пожаловать в Novamedika Q&A Bot!**\n\n"
            )

            if online_count > 0:
                welcome_text += f"👥 **Фармацевтов онлайн:** {online_count}\n✅ Можете задавать вопросы!\n\n"
            else:
                welcome_text += "⏳ **Сейчас фармацевтов нет онлайн**\n📝 Ваши вопросы будут сохранены\n\n"

            welcome_text += (
                "❓ **Чтобы задать вопрос:**\n"
                "1. Нажмите /ask\n"
                "2. Напишите ваш вопрос\n"
                "3. Получите ответ от фармацевта\n\n"

                "💡 **Примеры вопросов:**\n"
                "• 'Какое лекарство от головной боли?'\n"
                "• 'Можно ли принимать препарат X при давлении?'\n"
                "• 'Какие аналоги у лекарства Y?'\n\n"

                "🛠 **Все команды:** /help"
            )

            await message.answer(welcome_text)

    except Exception as e:
        logger.error(f"Error processing user message: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
