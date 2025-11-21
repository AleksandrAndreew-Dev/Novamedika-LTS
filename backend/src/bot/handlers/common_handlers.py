# bot/handlers/common_handlers.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.qa_models import User
from utils.time_utils import get_utc_now_naive
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
            [InlineKeyboardButton(text="👨‍⚕️ Я фарм специалист", callback_data="i_am_pharmacist")]
        ]
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool, pharmacist: object):
    """Улучшенный старт с кнопками"""
    await state.clear()

    if is_pharmacist and pharmacist:
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        pharmacy_name = pharmacist.pharmacy_info.get('name', 'Не указана')

        await message.answer(
            f"👨‍⚕️ <b>Добро пожаловать в панель фармацевта!</b>\n\n"
            f"📊 <b>Ваш статус:</b> {status_text}\n"
            f"🏥 <b>Аптека:</b> {pharmacy_name}\n\n"
            "💡 <b>Используйте кнопки ниже или команды:</b>\n"
            "• /online - перейти в онлайн\n"
            "• /questions - просмотреть вопросы\n"
            "• /help - подробная справка",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Добро пожаловать в Novamedika Q&A Bot!</b>\n\n"
            "Я помогу вам получить консультации от профессиональных фармацевтов.\n\n"
            "💡 <b>Выберите действие:</b>\n"
            "• Задать вопрос фармацевту\n"
            "• Посмотреть свои вопросы\n"
            "• Если вы фармацевт - зарегистрируйтесь",
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

# Добавить обработчики callback-кнопок
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
async def go_online_callback(callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool, pharmacist: object):
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
            "просматривать ожидающие вопросы.",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    except Exception as e:
        await callback.answer("❌ Ошибка при переходе в онлайн", show_alert=True)

@router.callback_query(F.data == "view_questions")
async def view_questions_callback(callback: CallbackQuery, is_pharmacist: bool):
    """Быстрый просмотр вопросов через кнопку"""
    if not is_pharmacist:
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    await callback.answer()
    # Имитируем команду /questions
    from aiogram.types import Message
    fake_message = Message(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        text="/questions"
    )
    # Здесь нужно вызвать обработчик команды /questions
    # Для простоты просто отправляем сообщение
    await callback.message.answer("📋 Используйте команду /questions для просмотра списка вопросов")

@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, is_pharmacist: bool):
    """Быстрый вопрос через кнопку"""
    if is_pharmacist:
        await callback.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "💬 Чтобы задать вопрос, используйте команду:\n"
        "<code>/ask</code>\n\n"
        "Или просто напишите ваш вопрос после нажатия кнопки:",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "my_questions")
async def my_questions_callback(callback: CallbackQuery):
    """Быстрый просмотр своих вопросов через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "📖 Используйте команду:\n"
        "<code>/my_questions</code>\n\n"
        "чтобы посмотреть историю ваших вопросов и ответы на них",
        parse_mode="HTML"
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

# ПЕРЕМЕСТИТЬ ЭТОТ ОБРАБОТЧИК В САМЫЙ КОНЕЦ
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
    """Обработка текстовых сообщений без команд - улучшенный онбоардинг"""

    # Пропускаем команды
    if message.text.startswith('/'):
        return

    current_state = await state.get_state()

    # Если есть состояние - не обрабатываем здесь
    if current_state is not None:
        logger.debug(f"Message in state {current_state} ignored by handle_user_message, user: {message.from_user.id}")
        return

    logger.info(f"Handle user message from {message.from_user.id} with no state, user: {user.uuid}")

    # Улучшенное приветственное сообщение
    if is_pharmacist and pharmacist:
        status_text = "🟢 онлайн" if pharmacist.is_online else "🔴 офлайн"
        await message.answer(
            f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
            f"Ваш текущий статус: <b>{status_text}</b>\n\n"
            "💡 <b>Быстрые команды:</b>\n"
            "• /online - принимать вопросы\n"
            "• /questions - список вопросов\n"
            "• /status - ваш статус\n"
            "• /help - полная справка\n\n"
            "Чтобы начать работу, перейдите в онлайн!",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Novamedika Q&A Bot</b>\n\n"
            "Я помогу вам получить консультацию фармацевта.\n\n"
            "💡 <b>Чтобы задать вопрос:</b>\n"
            "1. Нажмите /ask\n"
            "2. Опишите вашу проблему\n"
            "3. Получите профессиональный ответ\n\n"
            "📋 <b>Другие команды:</b>\n"
            "• /my_questions - ваши вопросы\n"
            "• /help - подробная инструкция\n\n"
            "Фармацевты ответят вам в ближайшее время! 🕒",
            parse_mode="HTML",
            reply_markup=get_user_keyboard()
        )
