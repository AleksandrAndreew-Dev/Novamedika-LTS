# user_questions.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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

@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext, db: AsyncSession):
    """Начать диалог с вопросом"""
    # Проверяем, не является ли пользователь фармацевтом
    from routers.pharmacist_auth import get_pharmacist_by_telegram_id
    pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

    if pharmacist:
        await message.answer("ℹ️ Вы зарегистрированы как фармацевт. Используйте команды /questions для ответов на вопросы.")
        return

    # Показываем количество онлайн фармацевтов
    online_threshold = get_utc_now_naive() - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(Pharmacist.uuid))
        .where(Pharmacist.is_online == True)
        .where(Pharmacist.last_seen >= online_threshold)
    )
    online_count = result.scalar() or 0

    # Более информативный статус
    if online_count > 0:
        status_text = f"👥 Фармацевтов онлайн: {online_count}\n💬 Ваш вопрос будет обработан в ближайшее время\n\n"
    elif online_count == 0:
        # Получаем общее количество активных фармацевтов (не обязательно онлайн)
        total_result = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_active == True)
        )
        total_pharmacists = total_result.scalar() or 0

        if total_pharmacists > 0:
            status_text = f"⏳ Сейчас нет фармацевтов онлайн (всего в системе: {total_pharmacists})\n📝 Ваш вопрос будет сохранен и обработан при появлении фармацевтов\n\n"
        else:
            status_text = "⏳ В системе пока нет фармацевтов\n📝 Ваш вопрос будет сохранен и обработан при подключении фармацевтов\n\n"

    await message.answer(
        f"{status_text}"
        "💊 Задайте ваш вопрос фармацевту:\n\n"
        "Просто напишите ваш вопрос и отправьте его. "
        "Фармацевты ответят вам в ближайшее время.\n\n"
        "❌ Чтобы отменить, используйте /cancel"
    )
    await state.set_state(UserQAStates.waiting_for_question)

@router.message(UserQAStates.waiting_for_question)
async def process_user_question(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка вопроса пользователя"""
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

        # Сохраняем ID вопроса для продолжения диалога
        await state.update_data(current_question_id=str(question.uuid))

        await message.answer(
            "✅ Ваш вопрос принят! Ожидайте ответа от фармацевта.\n\n"
            "Вы получите уведомление, когда на ваш вопрос ответят.\n"
            "Можете продолжать писать сообщения - они добавятся к этому же вопросу.\n\n"
            "❌ Чтобы завершить вопрос, используйте /done"
        )

        # Переходим в состояние диалога
        await state.set_state(UserQAStates.in_dialog)

        logger.info(f"New question from user {user.uuid}: {message.text[:100]}...")

    except Exception as e:
        logger.error(f"Error processing user question: {e}")
        await message.answer("❌ Произошла ошибка при отправке вопроса. Попробуйте позже.")

@router.message(UserQAStates.in_dialog)
async def process_dialog_message(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка сообщений в диалоге"""
    try:
        data = await state.get_data()
        question_id = data.get('current_question_id')

        if not question_id:
            await message.answer("❌ Не найден активный вопрос. Используйте /ask чтобы задать новый вопрос.")
            await state.clear()
            return

        # Находим вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден. Используйте /ask чтобы задать новый вопрос.")
            await state.clear()
            return

        # Добавляем сообщение к существующему вопросу
        question.text += f"\n\n[Дополнение]: {message.text}"
        await db.commit()

        await message.answer(
            "✅ Ваше сообщение добавлено к вопросу. Фармацевт увидит его когда будет отвечать.\n\n"
            "❌ Чтобы завершить вопрос, используйте /done"
        )

    except Exception as e:
        logger.error(f"Error processing dialog message: {e}")
        await message.answer("❌ Ошибка при обработке сообщения.")

@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext, db: AsyncSession):
    """Завершить текущий диалог"""
    current_state = await state.get_state()

    if current_state == UserQAStates.in_dialog:
        data = await state.get_data()
        question_id = data.get('current_question_id')

        if question_id:
            # Можно добавить логику отметки вопроса как завершенного
            try:
                result = await db.execute(
                    select(Question).where(Question.uuid == uuid.UUID(question_id))
                )
                question = result.scalar_one_or_none()
                if question:
                    # Можно добавить поле "user_completed" или подобное
                    logger.info(f"User completed question {question_id}")
            except Exception as e:
                logger.error(f"Error updating question completion: {e}")

    await state.clear()
    await message.answer(
        "✅ Диалог завершен. Если у вас появится новый вопрос, используйте /ask\n\n"
        "📋 Чтобы посмотреть историю вопросов, используйте /my_questions"
    )




@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("ℹ️ Нечего отменять.")
        return

    await state.clear()
    await message.answer("❌ Действие отменено.")

@router.message(Command("my_questions"))
async def cmd_my_questions(message: Message, db: AsyncSession):
    """Показать вопросы пользователя и ответы на них"""
    try:
        # Проверяем, не является ли пользователь фармацевтом
        from routers.pharmacist_auth import get_pharmacist_by_telegram_id
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        if pharmacist:
            await message.answer("ℹ️ Вы фармацевт. Используйте /questions для просмотра вопросов.")
            return

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
            status_text = "отвечен" if question.status == "answered" else "ожидает ответа"

            text = f"{status_emoji} Вопрос ({status_text}):\n{question.text}\n"
            text += f"📅 Дата: {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"

            if question.answers:
                text += f"\n💊 Ответ фармацевта:\n{question.answers[0].text}\n"
                text += f"📅 Ответ дан: {question.answers[0].created_at.strftime('%d.%m.%Y %H:%M')}"

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

@router.message(F.text & ~F.command)
async def handle_user_message(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка обычных сообщений от пользователей"""
    try:
        # Проверяем, не является ли пользователь фармацевтом
        from routers.pharmacist_auth import get_pharmacist_by_telegram_id
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        if pharmacist:
            # Если это фармацевт, игнорируем обычные сообщения
            logger.info(f"Pharmacist {pharmacist.uuid} sent message, ignoring as user question")
            return

        # Проверяем состояние
        current_state = await state.get_state()

        if current_state == UserQAStates.in_dialog:
            # Если в диалоге, обрабатываем как дополнение к вопросу
            await process_dialog_message(message, state, db)
        elif current_state == UserQAStates.waiting_for_question:
            # Если ждем вопроса, обрабатываем как новый вопрос
            await process_user_question(message, state, db)
        else:
            # Если не в состоянии диалога, предлагаем начать его с информацией об онлайн статусе
            online_threshold = get_utc_now_naive() - timedelta(minutes=5)
            result = await db.execute(
                select(func.count(Pharmacist.uuid))
                .where(Pharmacist.is_online == True)
                .where(Pharmacist.last_seen >= online_threshold)
            )
            online_count = result.scalar() or 0

            online_info = f"👥 Фармацевтов онлайн: {online_count}\n\n" if online_count > 0 else ""

            await message.answer(
                f"{online_info}"
                "💊 Чтобы задать вопрос фармацевту, используйте команду /ask\n\n"
                "📋 Для справки используйте /help"
            )

    except Exception as e:
        logger.error(f"Error processing user message: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(Command("help"))
async def universal_help(message: Message, db: AsyncSession):
    """Универсальная справка, которая определяет тип пользователя"""
    try:
        from routers.pharmacist_auth import get_pharmacist_by_telegram_id
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        # Получаем количество онлайн фармацевтов (общее для обоих случаев)
        online_threshold = get_utc_now_naive() - timedelta(minutes=5)
        result = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_online == True)
            .where(Pharmacist.last_seen >= online_threshold)
        )
        online_count = result.scalar() or 0

        if pharmacist:
            # Справка для фармацевтов
            help_text = (
                f"👥 Фармацевтов онлайн: {online_count}\n\n"
                "👨‍⚕️ Справка для фармацевтов:\n\n"
                "📋 Основные команды:\n"
                "/online - Перейти в онлайн\n"
                "/offline - Перейти в офлайн\n"
                "/status - Мой статус\n"
                "/questions - Вопросы для ответа\n"
                "/my_questions - Мои назначенные вопросы\n\n"
                "💡 В онлайн-режиме вы получаете уведомления о новых вопросах"
            )
        else:
            # Справка для обычных пользователей с информацией об онлайн фармацевтах
            online_status = (
                f"👥 Сейчас онлайн: {online_count} фармацевт(ов)\n\n"
                if online_count > 0
                else "⏳ В настоящее время фармацевтов нет онлайн, но вопросы сохраняются\n\n"
            )

            help_text = (
                f"{online_status}"
                "💊 Бот вопрос-ответ Novamedika\n\n"
                "📋 Доступные команды:\n\n"
                "❓ Задать вопрос:\n"
                "/ask - Начать новый вопрос\n"
                "/done - Завершить текущий диалог\n"
                "/cancel - Отменить текущее действие\n\n"
                "📊 Мои вопросы:\n"
                "/my_questions - Мои вопросы и ответы\n\n"
                "💡 После команды /ask все ваши сообщения будут добавляться к текущему вопросу до тех пор, пока вы не используете /done"
            )

        await message.answer(help_text)

    except Exception as e:
        logger.error(f"Error in universal help: {e}")
        # Упрощенная справка при ошибке
        await message.answer(
            "💊 Бот вопрос-ответ Novamedika\n\n"
            "Основные команды:\n"
            "/ask - Задать вопрос фармацевту\n"
            "/my_questions - Мои вопросы\n"
            "/help - Справка"
        )
