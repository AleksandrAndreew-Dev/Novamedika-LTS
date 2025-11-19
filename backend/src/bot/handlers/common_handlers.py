# common_handlers.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)
router = Router()

async def show_pharmacist_help(message: Message, db: AsyncSession):
    """Показать справку для фармацевтов"""
    help_text = (
        "👨‍⚕️ **Помощь для фармацевтов**\n\n"
        "**Основные команды:**\n"
        "/online - перейти в онлайн режим\n"
        "/offline - перейти в офлайн режим\n"
        "/questions - просмотреть вопросы для ответа\n"
        "/status - показать текущий статус\n\n"

        "**Управление вопросами:**\n"
        "• Используйте /questions чтобы увидеть список\n"
        "• Нажмите на вопрос для ответа\n"
        "• Введите текст ответа\n\n"

        "**Регистрация:**\n"
        "/register - регистрация нового фармацевта\n"
        "/start - главное меню"
    )
    await message.answer(help_text)

async def show_customer_help(message: Message, db: AsyncSession):
    """Показать справку для пользователей"""
    help_text = (
        "👤 **Помощь для пользователей**\n\n"
        "**Основные команды:**\n"
        "/ask - задать вопрос фармацевту\n"
        "/my_questions - посмотреть мои вопросы и ответы\n"
        "/done - завершить текущий вопрос\n\n"

        "**Как это работает:**\n"
        "1. Нажмите /ask и напишите вопрос\n"
        "2. Фармацевты получат уведомление\n"
        "3. Вы получите ответ в этом чате\n"
        "4. Используйте /done чтобы завершить диалог\n\n"

        "**Примечание:**\n"
        "Фармацевты работают в рабочее время, ответ может занять некоторое время"
    )
    await message.answer(help_text)

async def show_general_help(message: Message, db: AsyncSession):
    """Показать общую справку"""
    help_text = (
        "🤖 **Novamedika Q&A Bot**\n\n"
        "Этот бот соединяет пользователей с профессиональными фармацевтами.\n\n"

        "**Для пользователей:**\n"
        "/ask - задать вопрос о лекарствах\n"
        "/my_questions - ваши вопросы и ответы\n\n"

        "**Для фармацевтов:**\n"
        "/register - регистрация фармацевта\n"
        "/online - начать принимать вопросы\n\n"

        "**Общие команды:**\n"
        "/help - показать эту справку\n"
        "/cancel - отменить текущее действие\n"
        "/start - главное меню"
    )
    await message.answer(help_text)

@router.message(Command("help"))
async def universal_help(message: Message, db: AsyncSession, is_pharmacist: bool):
    """Универсальная помощь с правильным определением роли"""
    try:
        if is_pharmacist:
            await show_pharmacist_help(message, db)
        else:
            # Проверяем, есть ли у пользователя вопросы (значит он не новый)
            from sqlalchemy import select
            from db.qa_models import User, Question

            result = await db.execute(
                select(Question)
                .join(User)
                .where(User.telegram_id == message.from_user.id)
            )
            user_questions = result.scalars().first()

            if user_questions:
                await show_customer_help(message, db)
            else:
                await show_general_help(message, db)

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.answer("❌ Ошибка при получении справки")

@router.message(Command("cancel"))
async def universal_cancel(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Универсальная отмена для всех пользователей"""
    try:
        current_state = await state.get_state()
        if current_state is None:
            await message.answer("ℹ️ Нечего отменять.")
            return

        await state.clear()

        if is_pharmacist:
            await message.answer("❌ Действие отменено. Возврат к режиму фармацевта.")
        else:
            await message.answer("❌ Действие отменено.")

    except Exception as e:
        logger.error(f"Error in universal cancel: {e}")
        await message.answer("❌ Ошибка при отмене действия.")
