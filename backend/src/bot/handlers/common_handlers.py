from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message, is_pharmacist: bool):
    """Показать справку"""
    logger.info(f"Command /help from user {message.from_user.id}, is_pharmacist: {is_pharmacist}")

    if is_pharmacist:
        help_text = (
            "👨‍⚕️ Справка для фармацевта:\n\n"
            "Основные команды:\n"
            "/online - перейти в онлайн режим\n"
            "/offline - перейти в офлайн режим\n"
            "/status - показать текущий статус\n"
            "/questions - просмотреть вопросы пользователей\n\n"
            "Общие команды:\n"
            "/help - эта справка\n"
            "/cancel - отменить текущее действие\n"
            "/my_questions - просмотреть отвеченные вопросы"
        )
    else:
        help_text = (
            "👋 Справка для пользователя:\n\n"
            "Основные команды:\n"
            "/ask - задать вопрос фармацевту\n"
            "/my_questions - просмотреть мои вопросы и ответы\n\n"
            "Общие команды:\n"
            "/help - эта справка\n"
            "/cancel - отменить текущее действие\n"
            "/register - регистрация в системе"
        )

    await message.answer(help_text)

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
    """Обработка неизвестных команд"""
    logger.info(f"Unknown command from user {message.from_user.id}: {message.text}")
    await message.answer(
        "❌ Неизвестная команда.\n\n"
        "Используйте /help для просмотра доступных команд."
    )

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
