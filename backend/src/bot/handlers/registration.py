from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os
import uuid

from db.qa_models import Pharmacist, User
from services.user_service import get_or_create_user
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)
router = Router()


class RegistrationStates(StatesGroup):
    waiting_secret_word = State()
    waiting_pharmacy_chain = State()
    waiting_pharmacy_number = State()
    waiting_pharmacy_role = State()
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_patronymic = State()


async def register_pharmacist_from_telegram(telegram_data: dict, db: AsyncSession):
    """Регистрация фармацевта с проверкой дубликатов"""
    try:
        user = await get_or_create_user(
            db,
            telegram_id=telegram_data["telegram_user_id"],
            first_name=telegram_data.get("first_name"),
            last_name=telegram_data.get("last_name"),
            telegram_username=telegram_data.get("telegram_username"),
            user_type="pharmacist",
        )
        pharmacy_info = telegram_data.get("pharmacy_info", {})

        # Добавляем ФИО в информацию о фармацевте
        pharmacy_info["first_name"] = telegram_data.get("first_name", "")
        pharmacy_info["last_name"] = telegram_data.get("last_name", "")
        pharmacy_info["patronymic"] = telegram_data.get("patronymic", "")

        # Проверяем, есть ли уже фармацевт с таким user_id
        result = await db.execute(
            select(Pharmacist).where(Pharmacist.user_id == user.uuid)
        )
        existing_pharmacist = result.scalar_one_or_none()

        if existing_pharmacist:
            # Если запись уже есть, активируем ее и обновляем информацию
            existing_pharmacist.is_active = True
            existing_pharmacist.is_online = True
            existing_pharmacist.last_seen = get_utc_now_naive()
            existing_pharmacist.pharmacy_info = pharmacy_info
            pharmacist = existing_pharmacist
        else:
            # Создаем новую запись
            pharmacist = Pharmacist(
                uuid=uuid.uuid4(),
                user_id=user.uuid,
                pharmacy_info=pharmacy_info,
                is_active=True,
                is_online=True,
                last_seen=get_utc_now_naive(),
            )
            db.add(pharmacist)

        await db.commit()
        await db.refresh(pharmacist)
        return pharmacist

    except Exception as e:
        await db.rollback()
        logger.error(f"Registration error: {e}")
        raise


@router.message(Command("register"))
async def cmd_register(
    message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool
):
    """Начать регистрацию фармацевта с проверки секретного слова"""
    logger.info(
        f"Command /register from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if is_pharmacist:
        await message.answer("❌ Вы уже зарегистрированы как фармацевт!")
        return

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await message.answer(
        "🔐 Регистрация фармацевта\n\n"
        "Для начала регистрации введите секретное слово:",
        reply_markup=cancel_keyboard,
    )
    await state.set_state(RegistrationStates.waiting_secret_word)


@router.message(
    RegistrationStates.waiting_secret_word, F.text == "❌ Отмена регистрации"
)
@router.message(
    RegistrationStates.waiting_pharmacy_chain, F.text == "❌ Отмена регистрации"
)
@router.message(
    RegistrationStates.waiting_pharmacy_number, F.text == "❌ Отмена регистрации"
)
@router.message(
    RegistrationStates.waiting_pharmacy_role, F.text == "❌ Отмена регистрации"
)
@router.message(
    RegistrationStates.waiting_first_name, F.text == "❌ Отмена регистрации"
)
@router.message(RegistrationStates.waiting_last_name, F.text == "❌ Отмена регистрации")
@router.message(
    RegistrationStates.waiting_patronymic, F.text == "❌ Отмена регистрации"
)
async def cancel_registration(message: Message, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await message.answer("❌ Регистрация отменена.", reply_markup=ReplyKeyboardRemove())


@router.message(RegistrationStates.waiting_secret_word)
async def process_secret_word(message: Message, state: FSMContext):
    """Проверка секретного слова"""
    secret_word = message.text.strip()
    expected_secret = os.getenv("REGISTRATION_SECRET_WORD")

    if not expected_secret:
        logger.critical(
            "REGISTRATION_SECRET_WORD is NOT SET — registration blocked for safety"
        )
        await message.answer(
            "⚠️ Регистрация временно недоступна. Обратитесь к администратору."
        )
        return

    if secret_word != expected_secret:
        await message.answer("❌ Неверное секретное слово. Попробуйте еще раз:")
        return

    # Секретное слово верное, переходим к выбору сети аптек
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новамедика"), KeyboardButton(text="Эклиния")],
            [KeyboardButton(text="❌ Отмена регистрации")],
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "✅ Секретное слово принято!\n\n" "Теперь выберите сеть аптек:",
        reply_markup=keyboard,
    )
    await state.set_state(RegistrationStates.waiting_pharmacy_chain)


@router.message(RegistrationStates.waiting_pharmacy_chain)
async def process_pharmacy_chain(message: Message, state: FSMContext):
    """Обработка выбора сети аптек"""
    chain = message.text.strip()
    if chain not in ["Новамедика", "Эклиния"]:
        await message.answer("Пожалуйста, выберите сеть из предложенных вариантов:")
        return

    await state.update_data(pharmacy_chain=chain)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await message.answer(
        "🔢 Введите номер аптеки (только цифры):", reply_markup=cancel_keyboard
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
            [KeyboardButton(text="❌ Отмена регистрации")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
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
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await message.answer(
        "👤 Введите ваше имя (обязательно):", reply_markup=cancel_keyboard
    )
    await state.set_state(RegistrationStates.waiting_first_name)


@router.message(RegistrationStates.waiting_first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    first_name = message.text.strip()
    if not first_name:
        await message.answer("Пожалуйста, введите ваше имя:")
        return

    await state.update_data(first_name=first_name)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await message.answer(
        "👤 Введите вашу фамилию (обязательно):", reply_markup=cancel_keyboard
    )
    await state.set_state(RegistrationStates.waiting_last_name)


@router.message(RegistrationStates.waiting_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка ввода фамилии"""
    last_name = message.text.strip()
    if not last_name:
        await message.answer("Пожалуйста, введите вашу фамилию:")
        return

    await state.update_data(last_name=last_name)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await message.answer(
        "👤 Введите ваше отчество (или отправьте '-' чтобы пропустить):",
        reply_markup=cancel_keyboard,
    )
    await state.set_state(RegistrationStates.waiting_patronymic)


@router.message(RegistrationStates.waiting_patronymic)
async def process_patronymic(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка ввода отчества и завершение регистрации"""
    patronymic = message.text.strip()
    if patronymic == "-":
        patronymic = ""

    try:
        data = await state.get_data()

        # Формируем данные для регистрации
        pharmacy_info = {
            "name": f"{data['pharmacy_chain']} №{data['pharmacy_number']}",
            "number": data["pharmacy_number"],
            "chain": data["pharmacy_chain"],
            "role": data["pharmacy_role"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "patronymic": patronymic,
        }

        telegram_data = {
            "telegram_user_id": message.from_user.id,
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "patronymic": patronymic,
            "telegram_username": message.from_user.username,
            "pharmacy_info": pharmacy_info,
        }

        # Вызываем функцию регистрации
        pharmacist = await register_pharmacist_from_telegram(telegram_data, db)

        # Формируем приветственное сообщение с ФИО
        welcome_message = (
            "✅ Регистрация успешно завершена!\n\n"
            f"👤 Ваши данные:\n"
            f"• Имя: {data['first_name']}\n"
            f"• Фамилия: {data['last_name']}\n"
        )

        if patronymic:
            welcome_message += f"• Отчество: {patronymic}\n"

        welcome_message += (
            f"\n🏥 Данные аптеки:\n"
            f"• Сеть: {data['pharmacy_chain']}\n"
            f"• Аптека №: {data['pharmacy_number']}\n"
            f"• Роль: {data['pharmacy_role']}\n\n"
            "Теперь вы можете:\n"
            "• Просматривать вопросы (/questions)\n"
            "• Отвечать пользователям\n"
            "• Получать уведомления о новых вопросах\n"
            "• Управлять своим онлайн статусом (/online, /offline)"
        )

        await message.answer(welcome_message, reply_markup=ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer("❌ Ошибка регистрации. Попробуйте еще раз.")
        await state.clear()
