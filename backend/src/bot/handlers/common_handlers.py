# bot/handlers/common_handlers.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.qa_models import User
from utils.time_utils import get_utc_now_naive
from bot.handlers.qa_states import UserQAStates
import logging

logger = logging.getLogger(__name__)

router = Router()

def get_pharmacist_keyboard():
    """Клавиатура для фармацевтов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Перейти в онлайн", callback_data="go_online")],
            [InlineKeyboardButton(text="📋 Смотреть вопросы", callback_data="view_questions")],
            [InlineKeyboardButton(text="❓ Помощь фармацевта", callback_data="pharmacist_help")]
        ]
    )

def get_user_keyboard():
    """Клавиатура для пользователей"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton(text="📖 Мои вопросы", callback_data="my_questions")],
            [InlineKeyboardButton(text="👨‍⚕️ Я фарм специалист", callback_data="i_am_pharmacist")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="user_help")]
        ]
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool, pharmacist: object):
    """Упрощенный старт"""
    await state.clear()

    if is_pharmacist and pharmacist:
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        pharmacy_name = pharmacist.pharmacy_info.get('name', 'Не указана')

        await message.answer(
            f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
            f"🏥 {pharmacy_name}\n"
            f"📊 Статус: {status_text}\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Novamedika Q&A Bot</b>\n\n"
            "Получите консультацию профессионального фармацевта!\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_keyboard()
        )

@router.message(Command("help"))
async def cmd_help(message: Message, is_pharmacist: bool):
    """Подробная справка с кнопками"""
    if is_pharmacist:
        await message.answer(
            "👨‍⚕️ <b>Подробная справка для фармацевта</b>\n\n"
            "📋 <b>Основные команды:</b>\n"
            "• /online - начать принимать вопросы\n"
            "• /offline - остановить прием вопросов\n"
            "• /questions - список ожидающих вопросов\n"
            "• /my_questions - ваши ответы\n"
            "• /status - ваш текущий статус\n\n"
            "💡 <b>Как работать с вопросами:</b>\n"
            "1. Перейдите в онлайн (/online)\n"
            "2. Получайте уведомления о новых вопросах\n"
            "3. Просматривайте вопросы (/questions)\n"
            "4. Нажимайте «Ответить» под вопросом\n"
            "5. Пользователь получит ответ с вашими данными",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Подробная справка для пользователя</b>\n\n"
            "📋 <b>Основные команды:</b>\n"
            "• /ask - задать вопрос фармацевту\n"
            "• /my_questions - история вопросов и ответов\n"
            "• /clarify - уточнить предыдущий вопрос\n\n"
            "💊 <b>Процесс консультации:</b>\n"
            "1. Нажмите «Задать вопрос»\n"
            "2. Опишите проблему подробно\n"
            "3. Фармацевты получат уведомление\n"
            "4. Вы получите профессиональный ответ\n\n"
            "👨‍⚕️ <b>Если вы фармацевт</b> - нажмите «Я фарм специалист»",
            parse_mode="HTML",
            reply_markup=get_user_keyboard()
        )

@router.callback_query(F.data == "i_am_pharmacist")
async def i_am_pharmacist_callback(callback: CallbackQuery, is_pharmacist: bool):
    """Обработка нажатия 'Я фарм специалист'"""
    if is_pharmacist:
        await callback.answer("Вы уже зарегистрированы как фармацевт!", show_alert=True)
        await callback.message.answer(
            "👨‍⚕️ Вы уже зарегистрированы как фармацевт!\n\n"
            "Используйте кнопки ниже для работы:",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await callback.answer()
        await callback.message.answer(
            "👨‍⚕️ <b>Регистрация фармацевта</b>\n\n"
            "Для регистрации в качестве фармацевта используйте команду:\n"
            "<code>/register</code>\n\n"
            "В процессе регистрации вам нужно будет:\n"
            "• Выбрать сеть аптек\n"
            "• Указать номер аптеки\n"
            "• Выбрать вашу роль\n"
            "• Ввести ФИО\n"
            "• Ввести секретное слово\n\n"
            "После регистрации вы сможете:\n"
            "• Отвечать на вопросы пользователей\n"
            "• Получать уведомления о новых вопросах\n"
            "• Управлять своим онлайн-статусом",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "go_online")
async def go_online_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object
):
    """Быстрый переход в онлайн через кнопку"""
    if not is_pharmacist or not pharmacist:
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    try:
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()

        await callback.answer("✅ Вы теперь онлайн!")
        await callback.message.answer(
            "🟢 <b>Вы перешли в онлайн статус!</b>\n\n"
            "Теперь вы будете получать уведомления о новых вопросах и можете "
            "просматривать ожидающие вопросы.\n\n"
            "Используйте кнопку ниже чтобы посмотреть вопросы:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in go_online_callback: {e}")
        await callback.answer("❌ Ошибка при переходе в онлайн", show_alert=True)

@router.callback_query(F.data == "view_questions")
async def view_questions_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object
):
    """Быстрый просмотр вопросов через кнопку - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if not is_pharmacist:
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    await callback.answer()

    try:
        # Используем реальный запрос к базе данных
        from sqlalchemy import select
        from db.qa_models import Question, User

        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.asc())
            .limit(5)
        )
        questions = result.scalars().all()

        if not questions:
            await callback.message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
            return

        for i, question in enumerate(questions, 1):
            # Проверяем, является ли вопрос уточнением
            is_clarification = (
                question.context_data and
                question.context_data.get("is_clarification")
            )

            if is_clarification:
                original_question_id = question.context_data.get("original_question_id")
                original_question_text = question.context_data.get("original_question_text", "")

                question_text = (
                    f"🔍 <b>УТОЧНЕНИЕ К ВОПРОСУ</b>\n\n"
                    f"❓ Исходный вопрос: {original_question_text}\n\n"
                    f"💬 Уточнение: {question.text}\n\n"
                    f"🕒 Создано: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                question_text = (
                    f"❓ Вопрос #{i}:\n{question.text}\n\n"
                    f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

            # Получаем пользователя
            user_result = await db.execute(
                select(User).where(User.uuid == question.user_id)
            )
            user = user_result.scalar_one_or_none()

            if user:
                user_info = user.first_name or user.telegram_username or "Аноним"
                if user.last_name:
                    user_info = f"{user.first_name} {user.last_name}"
                question_text += f"\n👤 Пользователь: {user_info}"

            from bot.keyboards.qa_keyboard import make_question_keyboard
            await callback.message.answer(
                question_text,
                parse_mode="HTML",
                reply_markup=make_question_keyboard(question.uuid)
            )

        if len(questions) == 5:
            await callback.message.answer(
                "💡 Показаны первые 5 вопросов. Ответьте на них чтобы увидеть следующие."
            )

    except Exception as e:
        logger.error(f"Error in view_questions_callback: {e}")
        await callback.message.answer("❌ Ошибка при получении вопросов")

@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, state: FSMContext, is_pharmacist: bool):
    """Непосредственный переход к вводу вопроса"""
    if is_pharmacist:
        await callback.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(UserQAStates.waiting_for_question)
    await callback.message.answer(
        "💬 <b>Напишите ваш вопрос фармацевту:</b>\n\n"
        "Опишите вашу проблему, и мы найдем решение!\n\n"
        "<i>Для отмены используйте /cancel</i>",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "my_questions")
async def my_questions_callback(callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool):
    """Быстрый просмотр своих вопросов через кнопку"""
    await callback.answer()

    # Создаем сообщение с командой для обработки реальным обработчиком
    from aiogram.types import Message
    fake_message = Message(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,
        text="/my_questions"
    )

    # Импортируем и вызываем реальный обработчик
    from bot.handlers.user_questions import cmd_my_questions
    await cmd_my_questions(fake_message, db, user, is_pharmacist)

@router.callback_query(F.data == "user_help")
async def user_help_callback(callback: CallbackQuery):
    """Помощь для пользователей через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "👋 <b>Помощь для пользователей</b>\n\n"
        "📋 <b>Основные команды:</b>\n"
        "• /ask - задать вопрос фармацевту\n"
        "• /my_questions - история вопросов и ответов\n"
        "• /clarify - уточнить предыдущий вопрос\n\n"
        "💊 <b>Процесс консультации:</b>\n"
        "1. Нажмите «Задать вопрос»\n"
        "2. Опишите проблему подробно\n"
        "3. Фармацевты получат уведомление\n"
        "4. Вы получите профессиональный ответ\n\n"
        "👨‍⚕️ <b>Если вы фармацевт</b> - нажмите «Я фарм специалист»",
        parse_mode="HTML",
        reply_markup=get_user_keyboard()
    )

@router.callback_query(F.data == "pharmacist_help")
async def pharmacist_help_callback(callback: CallbackQuery):
    """Помощь для фармацевтов через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "👨‍⚕️ <b>Помощь для фармацевтов</b>\n\n"
        "Основные команды:\n"
        "• /online - начать принимать вопросы\n"
        "• /offline - остановить прием вопросов\n"
        "• /questions - список ожидающих вопросов\n"
        "• /my_questions - ваши ответы\n"
        "• /status - ваш статус\n\n"
        "Для подробной справки используйте /help",
        parse_mode="HTML"
    )

@router.message(Command("cancel"))
async def universal_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    logger.info(f"Command /cancel from user {message.from_user.id}")

    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Нечего отменять.")
        return

    await state.clear()
    await message.answer("✅ Текущее действие отменено.")

@router.message(F.command)
async def unknown_command(message: Message):
    """Обработка неизвестных команд - ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ"""
    logger.info(f"Unknown command from user {message.from_user.id}: {message.text}")
    await message.answer(
        "❌ Неизвестная команда.\n\n"
        "Используйте /help для просмотра доступных команд."
    )

@router.message(F.text)
async def handle_user_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object,
    user: User
):
    """Упрощенная обработка текстовых сообщений"""

    # Пропускаем команды
    if message.text.startswith('/'):
        return

    current_state = await state.get_state()

    # Если есть состояние - не обрабатываем здесь
    if current_state is not None:
        logger.debug(f"Message in state {current_state} ignored by handle_user_message, user: {message.from_user.id}")
        return

    # Упрощенное приветственное сообщение
    if is_pharmacist and pharmacist:
        status_text = "🟢 онлайн" if pharmacist.is_online else "🔴 офлайн"
        await message.answer(
            f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
            f"Статус: <b>{status_text}</b>\n\n"
            "Используйте кнопки ниже для работы:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Novamedika Q&A Bot</b>\n\n"
            "Задайте вопрос фармацевту и получите профессиональную консультацию!\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_keyboard()
        )
