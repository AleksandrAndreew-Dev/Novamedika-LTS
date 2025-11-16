# bot/handlers/__init__.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

class RegistrationStates(StatesGroup):
    waiting_for_pharmacy = State()
    confirm_registration = State()

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Начало регистрации фармацевта"""
    await message.answer(
        "👨‍⚕️ Добро пожаловать в систему Novamedika!\n\n"
        "Для регистрации как фармацевт отправьте номер аптеки, в которой вы работаете:"
    )
    await state.set_state(RegistrationStates.waiting_for_pharmacy)

@router.message(RegistrationStates.waiting_for_pharmacy)
async def process_pharmacy_number(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка номера аптеки"""
    pharmacy_number = message.text.strip()

    # Ищем аптеку по номеру
    from db.models import Pharmacy
    result = await db.execute(
        select(Pharmacy).where(Pharmacy.pharmacy_number == pharmacy_number)
    )
    pharmacy = result.scalar_one_or_none()

    if not pharmacy:
        await message.answer(
            "❌ Аптека с таким номером не найдена.\n"
            "Пожалуйста, проверьте номер и попробуйте еще раз:"
        )
        return

    await state.update_data(pharmacy_id=str(pharmacy.uuid))

    await message.answer(
        f"✅ Найдена аптека: {pharmacy.name}\n"
        f"📍 Город: {pharmacy.city}\n"
        f"📞 Телефон: {pharmacy.phone}\n\n"
        "Для подтверждения регистрации отправьте /confirm"
    )
    await state.set_state(RegistrationStates.confirm_registration)

@router.message(Command("confirm"))
@router.message(RegistrationStates.confirm_registration, F.text == "/confirm")
async def confirm_registration(message: Message, state: FSMContext, db: AsyncSession):
    """Подтверждение регистрации"""
    from router.pharmacist_auth import register_from_telegram

    data = await state.get_data()
    pharmacy_id = data.get('pharmacy_id')

    if not pharmacy_id:
        await message.answer("❌ Ошибка: данные аптеки не найдены. Начните заново с /start")
        await state.clear()
        return

    # Данные из Telegram
    telegram_data = {
        "telegram_user_id": message.from_user.id,
        "pharmacy_id": pharmacy_id,
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
        "telegram_username": message.from_user.username or ""
    }

    try:
        # Регистрируем фармацевта
        response = await register_from_telegram(telegram_data, db)

        await message.answer(
            "🎉 Регистрация успешно завершена!\n\n"
            "Теперь вы можете:\n"
            "• Получать вопросы от пользователей\n"
            "• Отвечать на вопросы\n"
            "• Просматривать назначенные вопросы\n\n"
            "Используйте команду /help для списка доступных команд"
        )

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer(
            "❌ Ошибка регистрации. Возможно, вы уже зарегистрированы.\n"
            "Для входа используйте /login"
        )

    await state.clear()

@router.message(Command("login"))
async def cmd_login(message: Message, db: AsyncSession):
    """Вход для зарегистрированных фармацевтов"""
    from router.pharmacist_auth import pharmacist_login

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
