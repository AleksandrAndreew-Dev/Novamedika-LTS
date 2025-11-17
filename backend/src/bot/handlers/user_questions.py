# user_questions.py - ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ
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
from routers.pharmacist_auth import get_pharmacist_by_telegram_id

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
    pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

    if pharmacist:
        await message.answer("ℹ️ Вы зарегистрированы как фармацевт. Используйте команды /questions для ответов на вопросы.")
        return

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
            "✅ Чтобы завершить вопрос, используйте /done\n"
            "❌ Чтобы отменить, используйте /cancel"
        )

    except Exception as e:
        logger.error(f"Error processing dialog message: {e}")
        await message.answer("❌ Ошибка при обработке сообщения.")

@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext, db: AsyncSession):
    """Завершить текущий диалог и отметить вопрос как завершенный пользователем"""
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
        from sqlalchemy.orm import selectinload

        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        if pharmacist:
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

# В функции handle_user_message заменить приветствие:
@router.message(F.text & ~F.command)
async def handle_user_message(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка обычных сообщений с улучшенным приветствием"""
    try:
        # Проверяем, не является ли пользователь фармацевтом
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        if pharmacist:
            logger.info(f"Pharmacist {pharmacist.uuid} sent message, ignoring as user question")
            return

        # Проверяем состояние
        current_state = await state.get_state()

        if current_state == UserQAStates.in_dialog:
            await process_dialog_message(message, state, db)
        elif current_state == UserQAStates.waiting_for_question:
            await process_user_question(message, state, db)
        else:
            # ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ (БЕЗ ИМЕНИ)
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

@router.message(Command("help"))
async def universal_help(message: Message, db: AsyncSession):
    """Улучшенная универсальная справка"""
    try:
        pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

        # Получаем количество онлайн фармацевтов
        online_threshold = get_utc_now_naive() - timedelta(minutes=5)
        result = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_online == True)
            .where(Pharmacist.last_seen >= online_threshold)
        )
        online_count = result.scalar() or 0

        if pharmacist:
            # 📋 ПОЛНАЯ СПРАВКА ДЛЯ ФАРМАЦЕВТОВ
            help_text = (
                f"👨‍⚕️ **Справка для фармацевтов**\n\n"

                f"📊 **Текущая статистика:**\n"
                f"• Онлайн фармацевтов: {online_count}\n"
                f"• Ваш статус: {'🟢 Онлайн' if pharmacist.is_online else '🔴 Офлайн'}\n"
                f"• Аптека: {pharmacist.pharmacy_info.get('chain', 'Не указана')} №{pharmacist.pharmacy_info.get('number', 'Не указан')}\n\n"

                "🛠 **Основные команды:**\n"
                "• /online - перейти в онлайн режим\n"
                "• /offline - перейти в офлайн режим\n"
                "• /status - подробный статус\n"
                "• /questions - список вопросов для ответа\n"
                "• /my_questions - мои назначенные вопросы\n\n"

                "💡 **Как это работает:**\n"
                "• В онлайн-режиме вы получаете уведомления о новых вопросах\n"
                "• Используйте /questions чтобы просмотреть все ожидающие вопросы\n"
                "• Нажмите на вопрос в списке чтобы ответить на него\n"
                "• Ответы автоматически отправляются пользователям\n\n"

                "⚡ **Советы:**\n"
                "• Регулярно проверяйте /questions для новых вопросов\n"
                "• Используйте /offline когда недоступны для ответов\n"
                "• Отвечайте максимально подробно и профессионально"
            )
        else:
            # 📋 ПОЛНАЯ СПРАВКА ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
            online_status = (
                f"👥 **Сейчас онлайн:** {online_count} фармацевт(ов)\n"
                "💬 Ваш вопрос будет обработан быстро!\n\n"
                if online_count > 0 else
                "⏳ **Сейчас фармацевтов нет онлайн**\n"
                "📝 Ваш вопрос будет сохранен и обработан при их появлении\n\n"
            )

            help_text = (
                f"💊 **Novamedika Q&A Bot**\n\n"

                f"{online_status}"
                "❓ **Как задать вопрос:**\n"
                "1. Используйте команду /ask\n"
                "2. Напишите ваш вопрос и отправьте\n"
                "3. Фармацевты ответят вам в ближайшее время\n"
                "4. Получите уведомление с ответом\n\n"

                "🛠 **Доступные команды:**\n"
                "• /ask - задать новый вопрос\n"
                "• /my_questions - мои вопросы и ответы\n"
                "• /done - завершить текущий вопрос\n"
                "• /cancel - отменить текущее действие\n"
                "• /help - эта справка\n\n"

                "💡 **Советы по вопросам:**\n"
                "• Опишите проблему максимально подробно\n"
                "• Укажите название лекарства, дозировку\n"
                "• После /ask все сообщения добавляются к вопросу\n"
                "• Используйте /done чтобы завершить вопрос\n\n"

                "⏱ **Время ответа:**\n"
                "• Обычно в течение 5-15 минут в рабочее время\n"
                "• Ответы предоставляются профессиональными фармацевтами\n"
                "• Все консультации бесплатны"
            )

        await message.answer(help_text)

    except Exception as e:
        logger.error(f"Error in universal help: {e}")
        # Упрощенная справка при ошибке
        await message.answer(
            "💊 **Novamedika Q&A Bot**\n\n"
            "Основные команды:\n"
            "• /ask - задать вопрос фармацевту\n"
            "• /my_questions - мои вопросы\n"
            "• /help - полная справка\n\n"
            "👨‍⚕️ Для фармацевтов: /start"
        )
