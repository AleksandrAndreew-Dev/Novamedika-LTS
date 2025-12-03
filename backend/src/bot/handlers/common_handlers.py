from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
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
            [
                InlineKeyboardButton(
                    text="🟢 Перейти в онлайн", callback_data="go_online"
                ),
                InlineKeyboardButton(
                    text="🔴 Перейти в офлайн", callback_data="go_offline"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Смотреть вопросы", callback_data="view_questions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статус системы", callback_data="system_status"
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="pharmacist_help"),
            ],
        ]
    )


# bot/handlers/common_handlers.py - ОБНОВИТЬ get_user_keyboard
def get_user_keyboard():
    """Клавиатура для пользователей С КНОПКОЙ РЕГИСТРАЦИИ ФАРМАЦЕВТА"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Задать вопрос", callback_data="ask_question"
                ),
                InlineKeyboardButton(
                    text="🔍 Уточнить вопрос", callback_data="clarify_question"
                ),
            ],
            [InlineKeyboardButton(text="📖 Мои вопросы", callback_data="my_questions")],
            [
                InlineKeyboardButton(
                    text="👨‍⚕️ Я фармацевт / Регистрация",
                    callback_data="i_am_pharmacist",
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="user_help"),
            ],
        ]
    )


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: object,
):
    """Упрощенный старт"""
    await state.clear()

    if is_pharmacist and pharmacist:
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        pharmacy_name = pharmacist.pharmacy_info.get("name", "Не указана")

        await message.answer(
            f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
            f"🏥 {pharmacy_name}\n"
            f"📊 Статус: {status_text}\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard(),
        )
    else:
        await message.answer(
            "👋 <b>Novamedika Q&A Bot</b>\n\n"
            "Получите консультацию профессионального фармацевта!\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_keyboard(),
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
            reply_markup=get_pharmacist_keyboard(),
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
            reply_markup=get_user_keyboard(),
        )


# bot/handlers/common_handlers.py - ИСПРАВЛЕННЫЙ i_am_pharmacist_callback
@router.callback_query(F.data == "i_am_pharmacist")
async def i_am_pharmacist_callback(
    callback: CallbackQuery, is_pharmacist: bool, state: FSMContext
):
    """Обработка нажатия 'Я фарм специалист' С КНОПКОЙ РЕГИСТРАЦИИ"""
    if is_pharmacist:
        await callback.answer("Вы уже зарегистрированы как фармацевт!", show_alert=True)
        await callback.message.answer(
            "👨‍⚕️ Вы уже зарегистрированы как фармацевт!\n\n"
            "Используйте кнопки ниже для работы:",
            reply_markup=get_pharmacist_keyboard(),
        )
    else:
        await callback.answer()

        # Создаем клавиатуру с кнопкой регистрации
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        register_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👨‍⚕️ Зарегистрироваться как фармацевт",
                        callback_data="start_registration",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❓ Как проходит регистрация?",
                        callback_data="registration_info",
                    )
                ],
            ]
        )

        await callback.message.answer(
            "👨‍⚕️ <b>Регистрация фармацевта</b>\n\n"
            "Для регистрации в качестве фармацевта нажмите кнопку ниже:\n\n"
            "📋 <b>В процессе регистрации вам нужно будет:</b>\n"
            "• Выбрать сеть аптек\n"
            "• Указать номер аптеки\n"
            "• Выбрать вашу роль\n"
            "• Ввести ФИО\n"
            "• Ввести секретное слово\n\n"
            "⏱️ <b>Регистрация займет 2-3 минуты</b>",
            parse_mode="HTML",
            reply_markup=register_keyboard,
        )


@router.callback_query(F.data == "go_online")
async def go_online_callback(
    callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool, pharmacist: object
):
    """Быстрый переход в онлайн через кнопку"""
    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
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
            reply_markup=get_pharmacist_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in go_online_callback: {e}")
        await callback.answer("❌ Ошибка при переходе в онлайн", show_alert=True)


@router.callback_query(F.data == "go_offline")
async def go_offline_callback(
    callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool, pharmacist: object
):
    """Быстрый переход в офлайн через кнопку"""
    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        pharmacist.is_online = False
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()

        await callback.answer("✅ Вы теперь офлайн!")
        await callback.message.answer(
            "🔴 <b>Вы перешли в офлайн статус!</b>\n\n"
            "Вы больше не будете получать уведомления о новых вопросах.\n\n"
            "Чтобы вернуться к работе, нажмите «Перейти в онлайн».",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in go_offline_callback: {e}")
        await callback.answer("❌ Ошибка при переходе в офлайн", show_alert=True)


@router.callback_query(F.data == "view_questions")
async def view_questions_callback(
    callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool, pharmacist: object
):
    """Быстрый просмотр вопросов через кнопку - ОБНОВЛЕННАЯ ВЕРСИЯ С ПРАВИЛЬНЫМИ КНОПКАМИ ДЛЯ УТОЧНЕНИЙ"""
    if not is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
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
            is_clarification = question.context_data and question.context_data.get(
                "is_clarification"
            )

            if is_clarification:
                original_question_id = question.context_data.get("original_question_id")
                original_question_text = question.context_data.get(
                    "original_question_text", ""
                )

                question_text = (
                    f"🔍 <b>УТОЧНЕНИЕ К ВОПРОСУ</b>\n\n"
                    f"❓ Исходный вопрос: {original_question_text}\n\n"
                    f"💬 Уточнение: {question.text}\n\n"
                    f"🕒 Создано: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

                # Для уточнений используем специальную клавиатуру
                from bot.keyboards.qa_keyboard import make_clarification_keyboard

                reply_markup = make_clarification_keyboard(question.uuid)
            else:
                question_text = (
                    f"❓ Вопрос #{i}:\n{question.text}\n\n"
                    f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

                # Для обычных вопросов используем обычную клавиатуру
                from bot.keyboards.qa_keyboard import make_question_keyboard

                reply_markup = make_question_keyboard(question.uuid)

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

            await callback.message.answer(
                question_text, parse_mode="HTML", reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error in view_questions_callback: {e}")
        await callback.message.answer("❌ Ошибка при получении вопросов")


@router.callback_query(F.data == "ask_question")
async def ask_question_callback(
    callback: CallbackQuery, state: FSMContext, is_pharmacist: bool
):
    """Непосредственный переход к вводу вопроса С ПОДСКАЗКОЙ"""
    if is_pharmacist:
        await callback.answer(
            "ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.",
            show_alert=True,
        )
        return

    await callback.answer()
    await state.set_state(UserQAStates.waiting_for_question)

    # Примеры вопросов
    examples = [
        "• Что лучше принять от головной боли?",
        "• Можно ли детям парацетамол?",
        "• Какие есть аналоги препарата...",
        "• Взаимодействие двух лекарств",
        "• Побочные эффекты от...",
    ]

    await callback.message.answer(
        "💬 <b>Напишите ваш вопрос фармацевту:</b>\n\n"
        "<b>Примеры вопросов:</b>\n" + "\n".join(examples) + "\n\n"
        "<i>Просто напишите ваш вопрос в чат ↓</i>\n"
        "<i>Для отмены используйте /cancel</i>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "my_questions")
async def my_questions_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Быстрый просмотр своих вопросов через кнопку"""
    await callback.answer()

    # Вместо создания fake_message, импортируем и вызываем обработчик напрямую
    from bot.handlers.user_questions import cmd_my_questions

    # Создаем сообщение с помощью callback
    class MockMessage:
        def __init__(self, callback):
            self.message_id = callback.message.message_id
            self.date = callback.message.date
            self.chat = callback.message.chat
            self.from_user = callback.from_user
            self.text = "/my_questions"
            self.bot = callback.bot  # Добавляем бота

    mock_message = MockMessage(callback)
    await cmd_my_questions(mock_message, db, user, is_pharmacist)


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
        reply_markup=get_user_keyboard(),
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
        parse_mode="HTML",
    )


@router.callback_query(F.data == "system_status")
async def system_status_callback(
    callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool
):
    """Статус системы через кнопку"""
    await callback.answer()

    # Вместо создания fake_message, импортируем и вызываем обработчик напрямую
    from bot.handlers.qa_handlers import debug_status

    class MockMessage:
        def __init__(self, callback):
            self.message_id = callback.message.message_id
            self.date = callback.message.date
            self.chat = callback.message.chat
            self.from_user = callback.from_user
            self.text = "/debug_status"
            self.bot = callback.bot  # Добавляем бота

    mock_message = MockMessage(callback)
    await debug_status(mock_message, db, is_pharmacist)


@router.callback_query(F.data == "clarify_question")
async def clarify_question_callback(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
):
    """Уточнение вопроса через кнопку"""
    await callback.answer()

    # Вместо создания fake_message, импортируем и вызываем обработчик напрямую
    from bot.handlers.user_questions import cmd_clarify

    class MockMessage:
        def __init__(self, callback):
            self.message_id = callback.message.message_id
            self.date = callback.message.date
            self.chat = callback.message.chat
            self.from_user = callback.from_user
            self.text = "/clarify"
            self.bot = callback.bot  # Добавляем бота

    mock_message = MockMessage(callback)
    await cmd_clarify(mock_message, state, db, user)


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


@router.callback_query(F.data == "start_registration")
async def start_registration_callback(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, is_pharmacist: bool
):
    """Запуск регистрации через кнопку"""
    if is_pharmacist:
        await callback.answer(
            "❌ Вы уже зарегистрированы как фармацевт!", show_alert=True
        )
        return

    await callback.answer()

    # Вместо создания fake_message, используем прямой вызов логики
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from bot.handlers.registration import RegistrationStates

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новамедика"), KeyboardButton(text="Эклиния")],
            [KeyboardButton(text="❌ Отмена регистрации")]
        ],
        resize_keyboard=True
    )

    await callback.message.answer(
        "👨‍⚕️ Регистрация фармацевта\n\n"
        "Выберите сеть аптек:",
        reply_markup=keyboard
    )
    await state.set_state(RegistrationStates.waiting_pharmacy_chain)


@router.callback_query(F.data == "registration_info")
async def registration_info_callback(callback: CallbackQuery):
    """Информация о процессе регистрации"""
    await callback.answer()

    await callback.message.answer(
        "📋 <b>Процесс регистрации фармацевта:</b>\n\n"
        "1. <b>Выбор сети аптек</b> - Новамедика или Эклиния\n"
        "2. <b>Номер аптеки</b> - только цифры\n"
        "3. <b>Ваша роль</b> - Фармацевт или Провизор\n"
        "4. <b>ФИО</b> - имя и фамилия (обязательно), отчество (по желанию)\n"
        "5. <b>Секретное слово</b> - для подтверждения прав доступа\n\n"
        "⏱️ <b>Весь процесс занимает 2-3 минуты</b>\n\n"
        "✅ <b>После регистрации вы сможете:</b>\n"
        "• Отвечать на вопросы пользователей\n"
        "• Получать уведомления о новых вопросах\n"
        "• Управлять своим онлайн-статусом\n"
        "• Просматривать историю своих ответов\n\n"
        "👉 <b>Чтобы начать, нажмите «Зарегистрироваться как фармацевт»</b>",
        parse_mode="HTML",
    )
