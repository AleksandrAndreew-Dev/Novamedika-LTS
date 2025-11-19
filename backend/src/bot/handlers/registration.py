# registration.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os

from routers.pharmacist_auth import get_pharmacist_by_telegram_id, register_pharmacist
from db.qa_models import Pharmacist, User

logger = logging.getLogger(__name__)
router = Router()

class RegistrationStates(StatesGroup):
    waiting_pharmacy_chain = State()
    waiting_pharmacy_number = State()
    waiting_pharmacy_role = State()
    waiting_secret_word = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    """Универсальный старт для всех пользователей"""
    pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

    if pharmacist:
        # Фармацевт
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        await message.answer(
            f"👨‍⚕️ Добро пожаловать назад, {pharmacist.user.first_name or 'фармацевт'}!\n\n"
            f"Статус: {status_text}\n"
            f"Аптека: {pharmacist.pharmacy_info.get('name', 'Не указана')}\n\n"
            "Доступные команды:\n"
            "/online - перейти в онлайн\n"
            "/offline - перейти в офлайн\n"
            "/questions - просмотреть вопросы\n"
            "/status - показать статус\n"
            "/help - помощь"
        )
    else:
        # Обычный пользователь
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💊 Задать вопрос"), KeyboardButton(text="👨‍⚕️ Я фармацевт")],
                [KeyboardButton(text="📋 Мои вопросы"), KeyboardButton(text="❓ Помощь")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "👋 Добро пожаловать в Novamedika Q&A Bot!\n\n"
            "Я помогу вам получить профессиональные ответы от фармацевтов.\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )




@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    """Начать регистрацию фармацевта"""
    pharmacist = await get_pharmacist_by_telegram_id(message.from_user.id, db)

    if pharmacist:
        await message.answer("❌ Вы уже зарегистрированы как фармацевт!")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новамедика"), KeyboardButton(text="Эклиния")],
            [KeyboardButton(text="❌ Отмена регистрации")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "👨‍⚕️ Регистрация фармацевта\n\n"
        "Выберите сеть аптек:",
        reply_markup=keyboard
    )
    await state.set_state(RegistrationStates.waiting_pharmacy_chain)

@router.message(RegistrationStates.waiting_pharmacy_chain, F.text == "❌ Отмена регистрации")
@router.message(RegistrationStates.waiting_pharmacy_number, F.text == "❌ Отмена регистрации")
@router.message(RegistrationStates.waiting_pharmacy_role, F.text == "❌ Отмена регистрации")
@router.message(RegistrationStates.waiting_secret_word, F.text == "❌ Отмена регистрации")
async def cancel_registration(message: Message, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(RegistrationStates.waiting_pharmacy_chain)
async def process_pharmacy_chain(message: Message, state: FSMContext):
    """Обработка выбора сети аптек"""
    chain = message.text.strip()
    if chain not in ["Новамедика", "Эклиния"]:
        await message.answer("Пожалуйста, выберите сеть из предложенных вариантов:")
        return

    await state.update_data(pharmacy_chain=chain)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]],
        resize_keyboard=True
    )

    await message.answer(
        "🔢 Введите номер аптеки (только цифры):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(RegistrationStates.waiting_pharmacy_number)

@router.message(RegistrationStates.waiting_pharmacy_number)
async def process_pharmacy_number(message: Message, state: FSMContext):
    """Обработка номера аптеки"""
    number = message.text.strip()
    if not number.isdigit():
        await message.answer("Пожалуйста, введите только цифры:")
        return

    await state.update_data(pharmacy_number=number)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Фармацевт")],
            [KeyboardButton(text="Провизор")],
            [KeyboardButton(text="❌ Отмена регистрации")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Выберите вашу роль:", reply_markup=keyboard)
    await state.set_state(RegistrationStates.waiting_pharmacy_role)

@router.message(RegistrationStates.waiting_pharmacy_role)
async def process_pharmacy_role(message: Message, state: FSMContext):
    """Обработка выбора роли"""
    role = message.text.strip()
    if role not in ["Фармацевт", "Провизор"]:
        await message.answer("Пожалуйста, выберите роль из предложенных вариантов:")
        return

    await state.update_data(pharmacy_role=role)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]],
        resize_keyboard=True
    )

    await message.answer(
        "🔐 Введите секретное слово для завершения регистрации:",
        reply_markup=cancel_keyboard
    )
    await state.set_state(RegistrationStates.waiting_secret_word)

@router.message(RegistrationStates.waiting_secret_word)
async def process_secret_word(message: Message, state: FSMContext, db: AsyncSession):
    """Проверка секретного слова и завершение регистрации"""
    secret_word = message.text.strip()
    expected_secret = os.getenv("REGISTRATION_SECRET_WORD", "default_secret")

    if secret_word != expected_secret:
        await message.answer("❌ Неверное секретное слово. Попробуйте еще раз:")
        return

    try:
        data = await state.get_data()

        # Формируем данные для регистрации с новой структурой
        pharmacy_info = {
            "name": f"{data['pharmacy_chain']} №{data['pharmacy_number']}",
            "number": data['pharmacy_number'],
            "city": "",  # Город больше не запрашиваем
            "chain": data['pharmacy_chain'],
            "role": data['pharmacy_role']  # Новое поле
        }

        telegram_data = {
            "telegram_user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "telegram_username": message.from_user.username,
            "pharmacy_info": pharmacy_info  # Передаем всю информацию об аптеке
        }

        # Вызываем функцию регистрации
        from routers.pharmacist_auth import register_pharmacist
        result = await register_pharmacist(telegram_data, db)

        await message.answer(
            "✅ Регистрация успешна!\n\n"
            f"Сеть: {data['pharmacy_chain']}\n"
            f"Аптека №: {data['pharmacy_number']}\n"
            f"Роль: {data['pharmacy_role']}\n\n"
            "Теперь вы можете:\n"
            "• Просматривать вопросы (/questions)\n"
            "• Отвечать пользователям\n"
            "• Получать уведомления о новых вопросах\n"
            "• Управлять своим онлайн статусом (/online, /offline)",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer("❌ Ошибка регистрации. Попробуйте еще раз.")
        await state.clear()

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
