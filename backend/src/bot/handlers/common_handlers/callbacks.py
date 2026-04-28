"""Callback-обработчики общего назначения: навигация, статистика, помощь, регистрация."""

import logging

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.qa_models import User, Question, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.registration import RegistrationStates
from bot.handlers.common_handlers.keyboards import (
    get_pharmacist_inline_keyboard,
    get_pharmacist_inline_keyboard_with_token,
    get_user_inline_keyboard,
)
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(
    callback: CallbackQuery, 
    state: FSMContext, 
    is_pharmacist: bool | None = None, 
    user: User | None = None,
    pharmacist: Pharmacist | None = None
):
    """Возврат в главное меню"""
    await state.clear()

    if not user or is_pharmacist is None:
        logger.error("Missing required dependencies in back_to_main_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return

    if is_pharmacist and pharmacist:
        # Генерируем клавиатуру с JWT токеном
        keyboard = get_pharmacist_inline_keyboard_with_token(
            telegram_id=int(user.telegram_id),
            pharmacist_uuid=str(pharmacist.uuid)
        )
        await callback.message.answer(
            "👨‍⚕️ <b>Панель фармацевта</b>\n\n" "Выберите действие:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(
            "👋 <b>Главное меню</b>\n\n"
            " Напишите ваш вопрос фармацевтическомуу специалисту в чат  или Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "back_to_pharmacist_main")
async def back_to_pharmacist_main_callback(
    callback: CallbackQuery,
    state: FSMContext,
    is_pharmacist: bool | None = None,
    user: User | None = None,
    pharmacist: Pharmacist | None = None,
):
    """Возврат в панель фармацевта"""
    await state.clear()

    if not user or not is_pharmacist or not pharmacist:
        await callback.answer("❌ Вы не фармацевт или ошибка сервера", show_alert=True)
        return

    status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
    pharmacy_name = pharmacist.pharmacy_info.get("name", "Не указана")

    # Генерируем клавиатуру с JWT токеном
    keyboard = get_pharmacist_inline_keyboard_with_token(
        telegram_id=int(user.telegram_id),
        pharmacist_uuid=str(pharmacist.uuid)
    )

    await callback.message.answer(
        f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
        f"🏥 {pharmacy_name}\n"
        f"📊 Статус: {status_text}\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "questions_stats")
async def questions_stats_callback(
    callback: CallbackQuery, 
    db: AsyncSession | None = None, 
    user: User | None = None, 
    is_pharmacist: bool | None = None
):
    """Показать статистику по вопросам"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in questions_stats_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    try:
        total_result = await db.execute(
            select(func.count(Question.uuid)).where(Question.user_id == user.uuid)
        )
        total = total_result.scalar() or 0

        pending_result = await db.execute(
            select(func.count(Question.uuid)).where(
                Question.user_id == user.uuid, Question.status == "pending"
            )
        )
        pending = pending_result.scalar() or 0

        answered_result = await db.execute(
            select(func.count(Question.uuid)).where(
                Question.user_id == user.uuid, Question.status == "answered"
            )
        )
        answered = answered_result.scalar() or 0

        completed_result = await db.execute(
            select(func.count(Question.uuid)).where(
                Question.user_id == user.uuid, Question.status == "completed"
            )
        )
        completed = completed_result.scalar() or 0

        in_progress_result = await db.execute(
            select(func.count(Question.uuid)).where(
                Question.user_id == user.uuid, Question.status == "in_progress"
            )
        )
        in_progress = in_progress_result.scalar() or 0

        if total == 0:
            await callback.message.answer(
                "📊 <b>Статистика</b>\n\n"
                "У вас пока нет вопросов.\n\n"
                "Задайте первый вопрос в чат!",
                parse_mode="HTML",
            )
            return

        stats_text = f"📊 <b>Статистика ваших вопросов</b>\n\n"
        stats_text += f"📋 <b>Всего:</b> {total}\n"
        stats_text += f"⏳ <b>Ожидают ответа:</b> {pending}\n"
        stats_text += f"🔄 <b>В обработке:</b> {in_progress}\n"
        stats_text += f"💬 <b>Отвечены:</b> {answered}\n"
        stats_text += f"✅ <b>Завершены:</b> {completed}\n\n"

        if total > 0:
            answer_rate = ((answered + completed) / total) * 100
            stats_text += f"📈 <b>Процент ответов:</b> {answer_rate:.1f}%\n"

        await callback.message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in questions_stats_callback: {e}")
        await callback.message.answer("❌ Ошибка при получении статистики")


@router.callback_query(F.data == "i_am_pharmacist")
async def i_am_pharmacist_callback(callback: CallbackQuery, state: FSMContext):
    """Начать регистрацию фармацевта"""
    await state.clear()
    await callback.message.answer(
        "👨‍⚕️ <b>Регистрация фармацевта</b>\n\n"
        "Для регистрации обратитесь к администратору.\n\n"
        "Или нажмите кнопку «Регистрация» ниже.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Регистрация",
                        callback_data="start_registration",
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "go_online")
async def go_online_callback(
    callback: CallbackQuery,
    db: AsyncSession | None = None,
    is_pharmacist: bool | None = None,
    pharmacist: Pharmacist | None = None,
    user: User | None = None,
):
    """Перейти в онлайн"""
    logger.info(f"go_online_callback called for user {callback.from_user.id}")
    logger.info(f"Dependencies: db={db is not None}, user={user is not None}, is_pharmacist={is_pharmacist}, pharmacist={pharmacist is not None}")
    
    if not db or not user or not is_pharmacist or not pharmacist:
        logger.error(f"Missing dependencies: db={bool(db)}, user={bool(user)}, is_pharmacist={is_pharmacist}, pharmacist={bool(pharmacist)}")
        await callback.answer("❌ Ошибка сервера. Попробуйте позже.", show_alert=True)
        return True  # Явно возвращаем True чтобы aiogram понял что handler обработал update

    pharmacist.is_online = True
    pharmacist.last_seen = get_utc_now_naive()
    await db.commit()

    # Генерируем клавиатуру с JWT токеном
    keyboard = get_pharmacist_inline_keyboard_with_token(
        telegram_id=int(user.telegram_id),
        pharmacist_uuid=str(pharmacist.uuid)
    )

    await callback.message.answer(
        "🟢 <b>Вы теперь онлайн!</b>\n\n"
        "Вы будете получать уведомления о новых вопросах.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "go_offline")
async def go_offline_callback(
    callback: CallbackQuery,
    db: AsyncSession | None = None,
    is_pharmacist: bool | None = None,
    pharmacist: Pharmacist | None = None,
    user: User | None = None,
):
    """Перейти в офлайн"""
    logger.info(f"go_offline_callback called for user {callback.from_user.id}")
    logger.info(f"Dependencies: db={db is not None}, user={user is not None}, is_pharmacist={is_pharmacist}, pharmacist={pharmacist is not None}")
    
    if not db or not user or not is_pharmacist or not pharmacist:
        logger.error(f"Missing dependencies: db={bool(db)}, user={bool(user)}, is_pharmacist={is_pharmacist}, pharmacist={bool(pharmacist)}")
        await callback.answer("❌ Ошибка сервера. Попробуйте позже.", show_alert=True)
        return True  # Явно возвращаем True чтобы aiogram понял что handler обработал update

    pharmacist.is_online = False
    pharmacist.last_seen = get_utc_now_naive()
    await db.commit()

    # Генерируем клавиатуру с JWT токеном
    keyboard = get_pharmacist_inline_keyboard_with_token(
        telegram_id=int(user.telegram_id),
        pharmacist_uuid=str(pharmacist.uuid)
    )

    await callback.message.answer(
        "🔴 <b>Вы теперь офлайн.</b>\n\n"
        "Вы не будете получать уведомления о новых вопросах.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("continue_user_dialog_"))
async def continue_user_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession | None = None,
    user: User | None = None,
    is_pharmacist: bool | None = None,
):
    """Продолжить диалог пользователя"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in continue_user_dialog_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("continue_user_dialog_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if question.status == "completed":
            await callback.answer("❌ Консультация уже завершена", show_alert=True)
            return

        await state.update_data(active_dialog_question_id=question_uuid)
        await state.set_state(UserQAStates.in_dialog)

        await callback.message.answer(
            "💬 <b>Продолжение диалога</b>\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
            "Напишите ваше сообщение фармацевту:",
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in continue_user_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при продолжении диалога", show_alert=True)


@router.callback_query(F.data == "view_questions")
async def view_questions_callback(
    callback: CallbackQuery,
    db: AsyncSession | None = None,
    user: User | None = None,
    is_pharmacist: bool | None = None,
):
    """Просмотреть вопросы"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in view_questions_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    from bot.handlers.user_question_handlers.commands import cmd_my_questions

    await cmd_my_questions(callback, db, user, is_pharmacist)


@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, state: FSMContext):
    """Задать вопрос"""
    await state.set_state(UserQAStates.waiting_for_question)
    await callback.message.answer(
        "📝 <b>Напишите ваш вопрос:</b>\n\n"
        "Опишите вашу проблему подробно.\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "my_questions")
async def my_questions_callback(
    callback: CallbackQuery, 
    db: AsyncSession | None = None, 
    user: User | None = None, 
    is_pharmacist: bool | None = None
):
    """Мои вопросы"""
    if not db or not user or is_pharmacist is None:
        logger.error("Missing required dependencies in my_questions_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    from bot.handlers.user_question_handlers.commands import cmd_my_questions

    await cmd_my_questions(callback, db, user, is_pharmacist)


@router.callback_query(F.data == "user_help")
async def user_help_callback(callback: CallbackQuery):
    """Помощь для пользователей через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "👋 <b>Помощь для пользователей</b>\n\n"
        "💊 <b>Основной процесс:</b>\n"
        "1. Просто напишите вопрос в чат\n"
        "2. Фармацевт ответит в ближайшее время\n"
        "3. После ответа вы увидите кнопки:\n"
        "   • Уточнить вопрос\n"
        "   • Завершить диалог\n\n"
        "💬 <b>Завершение диалога:</b>\n"
        "Нажмите кнопку «Завершить диалог» в сообщении с ответом,\n"
        "чтобы завершить консультацию по текущему вопросу.",
        parse_mode="HTML",
        reply_markup=get_user_inline_keyboard(),
    )


@router.callback_query(F.data == "pharmacist_help")
async def pharmacist_help_callback(callback: CallbackQuery):
    """Помощь для фармацевтов через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "👨‍⚕️ <b>Помощь для фармацевтов</b>\n\n"
        "💊 <b>Основной процесс:</b>\n"
        "1. Перейдите в онлайн (/online)\n"
        "2. Просматривайте вопросы (/questions)\n"
        "3. Нажмите «Ответить» под вопросом\n"
        "4. Ведите диалог с пользователем\n"
        "5. Завершите диалог когда консультация завершена\n\n"
        "💬 <b>В диалоге вы можете:</b>\n"
        "• Отправлять ответы пользователю\n"
        "• Запрашивать фото рецепта (кнопка «Запросить фото»)\n"
        "• Завершать диалог (кнопка «Завершить диалог»)\n\n"
        "Для подробной справки используйте /help",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "system_status")
async def system_status_callback(
    callback: CallbackQuery, 
    db: AsyncSession | None = None, 
    is_pharmacist: bool | None = None
):
    """Статус системы через кнопку"""
    if not db or is_pharmacist is None:
        logger.error("Missing required dependencies in system_status_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    from bot.handlers.qa_handlers.commands import debug_status

    await debug_status(callback, db, is_pharmacist)


@router.callback_query(F.data == "clarify_question")
async def clarify_question_callback(
    callback: CallbackQuery, 
    state: FSMContext, 
    db: AsyncSession | None = None, 
    user: User | None = None
):
    """Уточнение вопроса через кнопку"""
    if not db or not user:
        logger.error("Missing required dependencies in clarify_question_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
        
    from bot.handlers.clarify_handlers import clarify_command_handler

    await clarify_command_handler(callback, state, db, user)


@router.callback_query(F.data == "my_questions_from_completed")
async def my_questions_from_completed_callback(
    callback: CallbackQuery, 
    db: AsyncSession | None = None, 
    user: User | None = None, 
    is_pharmacist: bool | None = None
):
    """Обработка кнопки 'Мои вопросы' из завершенного диалога"""
    logger.info(f"my_questions_from_completed_callback called for user {callback.from_user.id}")
    logger.info(f"Dependencies: db={db is not None}, user={user is not None}, is_pharmacist={is_pharmacist}")
    
    if not db or not user or is_pharmacist is None:
        logger.error(f"Missing dependencies: db={bool(db)}, user={bool(user)}, is_pharmacist={is_pharmacist}")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return True  # Явно возвращаем True чтобы aiogram понял что handler обработал update
        
    from bot.handlers.user_question_handlers.commands import cmd_my_questions

    await cmd_my_questions(callback, db, user, is_pharmacist)
    return True  # Явно возвращаем True


@router.callback_query(F.data == "start_registration")
async def start_registration_callback(callback: CallbackQuery, state: FSMContext):
    """Начать регистрацию фармацевта"""
    await state.clear()
    await callback.message.answer(
        "📝 <b>Регистрация фармацевта</b>\n\n"
        "Введите секретное слово для регистрации:\n"
        "(или нажмите «❌ Отмена регистрации» для отмены)",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]],
            resize_keyboard=True,
        ),
    )
    await state.set_state(RegistrationStates.waiting_secret_word)
    await callback.answer()


@router.callback_query(F.data == "registration_info")
async def registration_info_callback(callback: CallbackQuery):
    """Информация о регистрации"""
    await callback.answer()
    await callback.message.answer(
        "📝 <b>Регистрация фармацевта</b>\n\n"
        "Для регистрации необходимо:\n"
        "1. Быть сотрудником аптеки\n"
        "2. Знать секретное слово (уточните у руководителя)\n"
        "3. Нажать кнопку «Регистрация»\n\n"
        "После регистрации вы сможете отвечать на вопросы пользователей.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "show_privacy_policy")
async def show_privacy_policy_callback(callback: CallbackQuery):
    """Показать политику конфиденциальности через кнопку"""
    await callback.answer()
    
    privacy_text = (
        "🔒 <b>Политика конфиденциальности</b>\n\n"
        "Мы заботимся о защите ваших персональных данных.\n\n"
        "📋 <b>Основные положения:</b>\n\n"
        "1️⃣ <b>Какие данные мы собираем:</b>\n"
        "• Telegram ID (для идентификации)\n"
        "• Имя и фамилия (если вы фармацевт)\n"
        "• Номер телефона (при оформлении заказов)\n"
        "• Текст вопросов и ответов\n\n"
        "2️⃣ <b>Как мы используем данные:</b>\n"
        "• Для предоставления консультаций фармацевтов\n"
        "• Для оформления заказов в аптеках\n"
        "• Для улучшения качества сервиса\n\n"
        "3️⃣ <b>Ваши права:</b>\n"
        "• Доступ к своим данным\n"
        "• Изменение или удаление данных\n"
        "• Отзыв согласия на обработку\n"
        "• Получение копии данных\n\n"
        "4️⃣ <b>Безопасность:</b>\n"
        "• Данные шифруются при передаче (HTTPS)\n"
        "• Телефон и Telegram ID шифруются в базе данных\n"
        "• Доступ только у авторизованных сотрудников\n\n"
        "5️⃣ <b>Внешние сервисы:</b>\n"
        "• Карты (Google Maps/Yandex Maps) — открываются по вашему запросу\n"
        "• Передаются только публичные данные (адреса аптек)\n"
        "• Персональные данные НЕ передаются внешним сервисам\n\n"
        "📄 <b>Полная версия политики:</b>\n"
        "https://spravka.novamedika.com/privacy\n\n"
        "📧 <b>Контакты для вопросов:</b>\n"
        "Email: privacy@novamedika.com\n\n"
        "ℹ️ Обработка данных осуществляется в соответствии с Законом РБ №99-З «О защите персональных данных»."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Полная версия на сайте",
                    url="https://spravka.novamedika.com/privacy",
                )
            ]
        ]
    )

    await callback.message.answer(privacy_text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query()
async def unmatched_callback(callback: CallbackQuery):
    """Catch-all для callback'ов, которые не совпали ни с одним handler"""
    logger.warning(
        f"Unmatched callback from user {callback.from_user.id}: "
        f"data='{callback.data}', "
        f"message_id={callback.message.message_id if callback.message else None}"
    )
    
    await callback.answer(
        "❌ Действие не распознано. Пожалуйста, обновите меню командой /start.",
        show_alert=True
    )
