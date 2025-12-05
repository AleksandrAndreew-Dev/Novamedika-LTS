
from aiogram.types import Message as AiogramMessage
from typing import Optional
from aiogram.types import WebAppInfo
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from bot.keyboards.qa_keyboard import (
    make_question_with_photo_and_clarify_keyboard,
    make_clarification_with_photo_and_answer_keyboard
)

# Остальной код остается без изменений...
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.qa_models import User
from utils.time_utils import get_utc_now_naive
from bot.handlers.qa_states import UserQAStates
from bot.services.notification_service import (
    notify_pharmacists_about_new_question,
    notify_about_clarification,
)
import logging

logger = logging.getLogger(__name__)


router = Router()


def get_reply_keyboard_with_webapp():
    """Создает reply-клавиатуру с Web App кнопкой"""
    web_app = WebAppInfo(url="https://spravka.novamedika.com/")

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Поиск лекарств", web_app=web_app)]],
        resize_keyboard=True,
        one_time_keyboard=False,  # Не скрывать после нажатия
        input_field_placeholder="Спросите фармацевта, например: витамины для детей",
    )


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
# Обновите функцию get_user_keyboard():


def get_user_keyboard():
    """Клавиатура для пользователей"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Поиск лекарств и бронирование",
                    callback_data="search_drugs",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 Мои вопросы", callback_data="my_questions"
                ),
                InlineKeyboardButton(
                    text="✍️ Уточнить вопрос", callback_data="clarify_question"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👨‍⚕️ Я фармацевт / Регистрация",
                    callback_data="i_am_pharmacist",
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="user_help"),
            ],
        ]
    )


@router.message(Command("hide_keyboard"))
async def hide_keyboard(message: Message):
    """Скрыть reply-клавиатуру"""
    from aiogram.types import ReplyKeyboardRemove

    await message.answer(
        "⌨️ Клавиатура скрыта. Используйте /search чтобы вернуть.",
        reply_markup=ReplyKeyboardRemove(),
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
        # Существующий код для фармацевтов...
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
        # ДЛЯ ПОЛЬЗОВАТЕЛЕЙ: показываем Web App кнопку
        reply_kb = get_reply_keyboard_with_webapp()

        await message.answer(
            "👋 <b>Novamedika Q&A Bot</b>\n\n"
            "💊 <b>Консультация профессионального фармацевта</b>\n\n"
            "📝 <b>Просто напишите ваш вопрос в чат!</b>\n\n"
            "Или используйте кнопки ниже:",
            parse_mode="HTML",
            reply_markup=reply_kb,
        )

        # Дополнительно показываем inline-кнопки для других действий
        await message.answer("Другие действия:", reply_markup=get_user_keyboard())


@router.message(Command("search"))
@router.callback_query(F.data == "search_drugs")
async def show_search_webapp(
    update: Message | CallbackQuery, state: FSMContext, is_pharmacist: bool
):
    """Показать Web App для поиска лекарств"""
    # Очищаем состояние
    await state.clear()

    # Создаем клавиатуру с Web App
    reply_kb = get_reply_keyboard_with_webapp()

    message_text = (
        "🔍 <b>Поиск и бронирование лекарств</b>\n\n"
        "Нажмите на кнопку ниже, чтобы открыть справку по аптекам.\n"
        "Узнайте цены, аналоги и забронируйте препарат заранее."
    )

    if isinstance(update, CallbackQuery):
        await update.message.answer(
            message_text, parse_mode="HTML", reply_markup=reply_kb
        )
        await update.answer()
    else:
        await update.answer(message_text, parse_mode="HTML", reply_markup=reply_kb)


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
            "👋 <b>Помощь по боту</b>\n\n"
            "💊 <b>Просто напишите вопрос в чат!</b>\n"
            "Никаких кнопок не нужно — бот автоматически отправит ваш вопрос фармацевтам.\n\n"
            "📋 <b>Дополнительные команды:</b>\n"
            "• /my_questions - история ваших вопросов и ответов\n"
            "• /clarify - уточнить предыдущий вопрос\n"
            "• /help - эта справка\n\n"
            "⏱️ <b>Как это работает:</b>\n"
            "1. Напишите вопрос в чат\n"
            "2. Фармацевты получат уведомление\n"
            "3. Вы получите ответ в ближайшее время\n"
            "4. Используйте «Мои вопросы» чтобы посмотреть ответ\n\n"
            "👨‍⚕️ <b>Если вы фармацевт</b> - нажмите «Я фарм специалист» в меню",
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
    """Быстрый просмотр вопросов через кнопку - ИСПРАВЛЕННАЯ ВЕРСИЯ С ПРАВИЛЬНЫМИ ФУНКЦИЯМИ"""
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
                # ИСПРАВЛЕНО: используем правильное имя функции
                reply_markup = make_clarification_with_photo_and_answer_keyboard(question.uuid)
            else:
                question_text = (
                    f"❓ Вопрос #{i}:\n{question.text}\n\n"
                    f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

                # Для обычных вопросов используем обычную клавиатуру
                # ИСПРАВЛЕНО: используем правильное имя функции
                reply_markup = make_question_with_photo_and_clarify_keyboard(question.uuid)

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
    """Непосредственный переход к вводу вопроса"""
    if is_pharmacist:
        await callback.answer(
            "ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.",
            show_alert=True,
        )
        return

    await callback.answer()
    await state.set_state(UserQAStates.waiting_for_question)

    await callback.message.answer(
        "📝 <b>Напишите ваш вопрос:</b>\n\n"
        "Опишите вашу проблему подробно, чтобы фармацевт мог дать точный ответ.\n\n"
        "<i>Просто напишите ваш вопрос в чат ↓</i>\n"
        "<i>Для отмены используйте /cancel</i>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "my_questions")
async def my_questions_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Быстрый просмотр своих вопросов через кнопку"""
    # Вместо модификации message.from_user, передаем callback напрямую
    from bot.handlers.user_questions import cmd_my_questions
    await cmd_my_questions(callback, db, user, is_pharmacist)


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
    # Используем существующую функцию debug_status напрямую
    from bot.handlers.qa_handlers import debug_status
    await debug_status(callback, db, is_pharmacist)




@router.callback_query(F.data == "clarify_question")
async def clarify_question_callback(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
):
    """Уточнение вопроса через кнопку"""
    # Используем существующую функцию напрямую
    from bot.handlers.clarify_handlers import clarify_command_handler
    await clarify_command_handler(callback, state, db, user)


# В файл common_handlers.py добавить в universal_cancel

@router.message(Command("cancel"))
async def universal_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    logger.info(f"Command /cancel from user {message.from_user.id}")

    current_state = await state.get_state()

    if current_state == UserQAStates.waiting_for_prescription_photo:
        await state.clear()
        await message.answer("❌ Отправка фото рецепта отменена.")
        return

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
    callback: CallbackQuery,
    state: FSMContext,
    is_pharmacist: bool
):
    """Запуск регистрации через кнопку - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if is_pharmacist:
        await callback.answer(
            "❌ Вы уже зарегистрированы как фармацевт!", show_alert=True
        )
        return

    await callback.answer()

    # НЕ создаем фиктивный Message, а напрямую переходим к регистрации
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]],
        resize_keyboard=True
    )

    await callback.message.answer(
        "🔐 Регистрация фармацевта\n\n"
        "Для начала регистрации введите секретное слово:",
        reply_markup=cancel_keyboard
    )

    # Устанавливаем состояние регистрации
    from bot.handlers.registration import RegistrationStates
    await state.set_state(RegistrationStates.waiting_secret_word)


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
