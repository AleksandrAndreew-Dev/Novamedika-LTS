from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool, pharmacist: object):
    """Улучшенный старт с Menu Commands"""
    await state.clear()  # Очищаем любые предыдущие состояния

    if is_pharmacist and pharmacist:
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        await message.answer(
            f"👨‍⚕️ Добро пожаловать, {pharmacist.user.first_name or 'фармацевт'}!\n\n"
            f"📊 Статус: {status_text}\n"
            f"🏥 Аптека: {pharmacist.pharmacy_info.get('name', 'Не указана')}\n\n"
            "💡 Используйте команды меню для работы:\n"
            "• /online - принимать вопросы\n"
            "• /questions - список вопросов\n"
            "• /my_questions - ваши ответы\n"
            "• /status - статистика\n"
            "• /help - помощь"
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в Novamedika Q&A Bot!\n\n"
            "💡 Используйте команды меню:\n"
            "• /ask - задать вопрос фармацевту\n"
            "• /my_questions - история вопросов\n"
            "• /register - регистрация фармацевта\n"
            "• /help - помощь\n\n"
            "Фармацевты ответят на ваши вопросы в рабочее время 🕒"
        )

@router.message(Command("help"))
async def cmd_help(message: Message, is_pharmacist: bool):
    if is_pharmacist:
        await message.answer(
            "👨‍⚕️ Помощь для фармацевта:\n\n"
            "/online - начать принимать вопросы\n"
            "/offline - остановить прием вопросов\n"
            "/questions - просмотреть вопросы\n"
            "/status - ваш текущий статус\n"
            "/my_questions - ваши ответы\n"
            "/cancel - отмена действия"
        )
    else:
        await message.answer(
            "👋 Помощь для пользователя:\n\n"
            "/ask - задать вопрос фармацевту\n"
            "/my_questions - история вопросов\n"
            "/register - регистрация фармацевта\n"
            "/cancel - отмена действия"
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

# ИСПРАВИТЬ: Добавить фильтр для исключения команд
@router.message(F.text & ~F.command)
async def handle_user_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object,
):
    """Обработка текстовых сообщений без команд и состояний"""
    current_state = await state.get_state()

    # Если есть какое-либо состояние - не обрабатываем здесь
    if current_state is not None:
        logger.debug(f"Message in state {current_state} ignored by handle_user_message, user: {message.from_user.id}")
        return

    logger.info(f"Handle user message from {message.from_user.id} with no state")

    # Показываем приветственное сообщение
    if is_pharmacist and pharmacist:
        await message.answer(
            "👨‍⚕️ Добро пожаловать, фармацевт!\n\n"
            "Используйте:\n"
            "/online - перейти в онлайн\n"
            "/offline - перейти в офлайн\n"
            "/questions - просмотреть вопросы\n"
            "/status - ваш статус\n"
            "/help - справка"
        )
    else:
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Я бот-помощник для консультаций с фармацевтами.\n\n"
            "Используйте:\n"
            "/ask - задать вопрос фармацевту\n"
            "/my_questions - мои вопросы\n"
            "/register - регистрация\n"
            "/help - справка"
        )
