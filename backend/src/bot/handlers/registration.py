# bot/handlers/registration.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging


logger = logging.getLogger(__name__)

class RegistrationStates(StatesGroup):
    waiting_for_chain = State()
    waiting_for_pharmacy = State()
    confirm_registration = State()

router = Router()
# bot/handlers/registration.py (упрощенная версия)
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Упрощенная регистрация"""
    await message.answer(
        "👨‍⚕️ Добро пожаловать в систему Novamedika!\n\n"
        "Для регистрации как фармацевт отправьте:\n"
        "• Название аптеки\n"
        "• Номер аптеки\n"
        "• Город\n\n"
        "Пример:\n"
        "Новамедика №1, Москва"
    )
    await state.set_state(RegistrationStates.waiting_pharmacy_info)

@router.message(RegistrationStates.waiting_pharmacy_info)
# registration.py - ОБНОВИТЬ функцию process_pharmacy_info
async def process_pharmacy_info(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка информации об аптеке"""
    try:
        text = message.text.strip()
        pharmacy_data = parse_pharmacy_info(text)

        telegram_data = {
            "telegram_user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "telegram_username": message.from_user.username,
            "pharmacy_name": pharmacy_data.get("pharmacy_name", ""),
            "pharmacy_number": pharmacy_data.get("pharmacy_number", ""),
            "pharmacy_city": pharmacy_data.get("pharmacy_city", ""),
            "pharmacy_chain": "Новамедика"  # или извлечь из данных
        }

        # Вызываем обновленную функцию регистрации
        from routers.pharmacist_auth import register_pharmacist
        result = await register_pharmacist(telegram_data, db)

        await message.answer("✅ Регистрация успешна!")
        await state.clear()

    except Exception as e:
        await message.answer("❌ Ошибка регистрации. Попробуйте еще раз.")

@router.message(Command("login"))
async def cmd_login(message: Message, db: AsyncSession):
    """Вход для зарегистрированных фармацевтов"""
    from routers.pharmacist_auth import pharmacist_login

    try:
        result = await pharmacist_login(message.from_user.id, db)

        # Сохраняем токен (в реальном приложении нужно безопасное хранилище)
        await message.answer(
            "✅ Вход выполнен успешно!\n\n"
            "Теперь вы можете работать с вопросами пользователей.\n"
            "Используйте /help для списка команд"
        )

    except Exception as e:
        await message.answer(
            "❌ Не удалось войти. Возможно, вы не зарегистрированы.\n"
            "Для регистрации используйте /start"
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start - Регистрация фармацевта\n"
        "/login - Вход в систему\n"
        "/help - Эта справка\n\n"
        "После регистрации вы сможете:\n"
        "• Получать уведомления о новых вопросах\n"
        "• Отвечать на вопросы пользователей\n"
        "• Просматривать историю ответов"
    )
    await message.answer(help_text)
