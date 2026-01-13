from sqlalchemy import select
from aiogram.types import WebAppInfo
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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
from db.qa_models import User, Question
from utils.time_utils import get_utc_now_naive
from bot.handlers.qa_states import UserQAStates

import logging

logger = logging.getLogger(__name__)


router = Router()


def get_reply_keyboard_with_webapp():
    """Создает reply-клавиатуру с Web App кнопкой"""
    web_app = WebAppInfo(url="https://spravka.novamedika.com/")


    return ReplyKeyboardMarkup(
        keyboard=[[InlineKeyboardButton(text="🔍 Поиск лекарств", web_app=web_app)]],
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
            [InlineKeyboardButton(text="📋 Мои вопросы", callback_data="my_questions")],
            [
                InlineKeyboardButton(
                    text="📊 Статус системы", callback_data="system_status"
                ),
                InlineKeyboardButton(text="❓ Помощь", callback_data="pharmacist_help"),
            ],
        ]
    )


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


@router.message(Command("hide_keyboard"))
async def hide_keyboard(message: Message):
    """Скрыть reply-клавиатуру"""
    from aiogram.types import ReplyKeyboardRemove

    await message.answer(
        "⌨️ Клавиатура скрыта. Используйте /search чтобы вернуть.",
        reply_markup=ReplyKeyboardRemove(),
    )


# В common_handlers.py добавляем:


@router.message(Command("history"))
async def cmd_history(
    message: Message, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Показать историю всех диалогов"""
    try:
        if is_pharmacist:
            # Все диалоги фармацевта
            result = await db.execute(
                select(Question)
                .where(Question.taken_by == user.uuid)
                .order_by(Question.taken_at.desc())
                .limit(20)
            )
        else:
            # Все диалоги пользователя
            result = await db.execute(
                select(Question)
                .where(Question.user_id == user.uuid)
                .order_by(Question.created_at.desc())
                .limit(20)
            )

        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📭 У вас пока нет диалогов.\n\n"
                "Начните новый диалог, отправив вопрос в чат."
            )
            return

        message_text = f"📚 <b>Ваши диалоги</b>\n\n"
        message_text += f"Всего диалогов: {len(questions)}\n\n"

        # Группируем по статусу
        active_dialogs = []
        completed_dialogs = []

        for q in questions:
            if q.status == "completed":
                completed_dialogs.append(q)
            else:
                active_dialogs.append(q)

        if active_dialogs:
            message_text += "💬 <b>Активные диалоги:</b>\n"
            for i, q in enumerate(active_dialogs[:5], 1):
                preview = q.text[:60] + "..." if len(q.text) > 60 else q.text
                message_text += f"{i}. {preview}\n"
                message_text += f"   📅 {q.created_at.strftime('%d.%m.%Y')}\n"

        if completed_dialogs:
            message_text += "\n✅ <b>Завершенные диалоги:</b>\n"
            for i, q in enumerate(completed_dialogs[:5], 1):
                preview = q.text[:60] + "..." if len(q.text) > 60 else q.text
                message_text += f"{i}. {preview}\n"
                message_text += f"   📅 {q.created_at.strftime('%d.%m.%Y')}\n"

        if len(questions) > 10:
            message_text += f"\n📋 ... и еще {len(questions) - 10} диалогов"

        await message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 Посмотреть все диалоги",
                            callback_data="view_all_dialogs",
                        )
                    ]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Error in cmd_history: {e}")
        await message.answer("❌ Ошибка при загрузке истории диалогов")


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
            "👋 <b>Лучше спросите в аптеке!</b>\n\n"
            "💊 <b>Консультация профессионального фармацевта</b>\n\n"
            "Просто напишите в чат, например:\n"
            '<i>"Что можно принять от головной боли?"</i>',
            parse_mode="HTML",
            reply_markup=reply_kb,
        )

        # Дополнительно показываем inline-кнопки для других действий
        await message.answer("Или выберите действие:", reply_markup=get_user_keyboard())


@router.message(Command("search"))
@router.callback_query(F.data == "search_drugs")
async def show_search_webapp(
    update: Message | CallbackQuery, state: FSMContext, is_pharmacist: bool
):
    """Показать Web App для поиска лекарств"""
    # Очищаем состояние
    await state.clear()

    # ✅ Добавляем проверку на фармацевта
    if is_pharmacist:
        if isinstance(update, CallbackQuery):
            await update.answer(
                "🔍 Используйте /questions для работы с вопросами", show_alert=True
            )
        else:
            await update.answer("🔍 Используйте /questions для работы с вопросами")
        return

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


# В common_handlers.py добавляем:
@router.message(Command("continue"))
async def cmd_continue(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Продолжить активный диалог"""
    if is_pharmacist:
        await message.answer(
            "👨‍⚕️ Вы фармацевт. Используйте /questions для работы с вопросами."
        )
        return

    try:
        # Ищем последний активный диалог
        result = await db.execute(
            select(Question)
            .where(
                Question.user_id == user.uuid,
                Question.status.in_(["in_progress", "answered"]),
                Question.taken_by.is_not(None),
            )
            .order_by(Question.answered_at.desc())
            .limit(1)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer(
                "📭 <b>Нет активных диалогов</b>\n\n" "Задайте вопрос в чат.",
                parse_mode="HTML",
            )
            return

        # Устанавливаем состояние
        await state.update_data(active_dialog_question_id=str(question.uuid))
        await state.set_state(UserQAStates.in_dialog)

        # Получаем информацию о фармацевте
        pharmacist_result = await db.execute(
            select(Pharmacist).where(Pharmacist.uuid == question.taken_by)
        )
        pharmacist = pharmacist_result.scalar_one_or_none()

        pharmacist_name = "Фармацевт"
        if pharmacist and pharmacist.pharmacy_info:
            first_name = pharmacist.pharmacy_info.get("first_name", "")
            last_name = pharmacist.pharmacy_info.get("last_name", "")
            patronymic = pharmacist.pharmacy_info.get("patronymic", "")

            name_parts = []
            if last_name:
                name_parts.append(last_name)
            if first_name:
                name_parts.append(first_name)
            if patronymic:
                name_parts.append(patronymic)

            pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"

        await message.answer(
            f"💬 <b>ПРОДОЛЖЕНИЕ ДИАЛОГА</b>\n\n"
            f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_name}\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text[:200]}...\n\n"
            "Напишите ваше сообщение фармацевту:\n"
            "(или /cancel для отмены)",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in cmd_continue: {e}")
        await message.answer("❌ Ошибка при продолжении диалога")


@router.message(Command("help"))
async def cmd_help(message: Message, is_pharmacist: bool):
    """Подробная справка с кнопками"""
    if is_pharmacist:
        await message.answer(
            "👨‍⚕️ <b>Как отвечать на вопросы?</b>\n\n"
            "1. Нажмите «🟢 Перейти в онлайн»\n"
            "2. Как придет уведомление — нажмите «💬 Ответить»\n"
            "3. Напишите ответ пользователю",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard(),
        )
    else:
        await message.answer(
            "💬 <b>Как задать вопрос?</b>\n\n"
            "Просто напишите в чат, например:\n"
            '<i>"Что можно принять от температуры?"</i>\n\n'
            "⏳ <b>Что дальше?</b>\n"
            "Фармацевт ответит, как только освободится.",
            "👨‍⚕️ <b>Если вы фармацевт</b> - нажмите «Я фарм специалист» в меню",
            parse_mode="HTML",
            reply_markup=get_user_keyboard(),
        )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(
    callback: CallbackQuery, state: FSMContext, is_pharmacist: bool, user: User
):
    """Возврат в главное меню"""
    await state.clear()

    if is_pharmacist:
        await callback.message.answer(
            "👨‍⚕️ <b>Панель фармацевта</b>\n\n" "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_keyboard(),
        )
    else:
        await callback.message.answer(
            "👋 <b>Главное меню</b>\n\n"
            " Напишите ваш вопрос фармацевтическомуу специалисту в чат  или Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "back_to_pharmacist_main")
async def back_to_pharmacist_main_callback(
    callback: CallbackQuery,
    state: FSMContext,
    is_pharmacist: bool,
    user: User,
    pharmacist: object,
):
    """Возврат в панель фармацевта"""
    await state.clear()

    if not is_pharmacist or not pharmacist:
        await callback.answer("❌ Вы не фармацевт", show_alert=True)
        return

    status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
    pharmacy_name = pharmacist.pharmacy_info.get("name", "Не указана")

    await callback.message.answer(
        f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
        f"🏥 {pharmacy_name}\n"
        f"📊 Статус: {status_text}\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_pharmacist_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "questions_stats")
async def questions_stats_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Показать статистику по вопросам"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    try:
        from sqlalchemy import func

        # Получаем статистику
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

        # Получаем последнюю активность
        last_result = await db.execute(
            select(Question.created_at)
            .where(Question.user_id == user.uuid)
            .order_by(Question.created_at.desc())
            .limit(1)
        )
        last_activity = last_result.scalar_one_or_none()

        stats_text = (
            "📊 <b>СТАТИСТИКА ВОПРОСОВ</b>\n\n"
            f"📋 Всего вопросов: {total}\n"
            f"⏳ Ожидают ответа: {pending}\n"
            f"💬 Получены ответы: {answered}\n"
            f"✅ Завершено: {completed}\n\n"
        )

        if last_activity:
            stats_text += (
                f"🕒 Последняя активность: {last_activity.strftime('%d.%m.%Y %H:%M')}\n"
            )

        if total > 0:
            stats_text += (
                f"📈 Процент ответов: {int((answered + completed) / total * 100)}%\n"
            )

        await callback.message.answer(
            stats_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 К списку вопросов",
                            callback_data="my_questions_callback",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 В меню", callback_data="back_to_main"
                        )
                    ],
                ]
            ),
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in questions_stats_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


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


# Добавить в common_handlers.py или user_questions.py:


@router.callback_query(F.data.startswith("continue_user_dialog_"))
async def continue_user_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Продолжение диалога пользователем после ответа фармацевта"""
    if is_pharmacist:
        await callback.answer(
            "👨‍⚕️ Вы фармацевт. Используйте /questions для ответов.", show_alert=True
        )
        return

    question_uuid = callback.data.replace("continue_user_dialog_", "")

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer(
                "❌ Вопрос не найден или не принадлежит вам", show_alert=True
            )
            return

        # Устанавливаем состояние для продолжения диалога
        await state.update_data(active_dialog_question_id=question_uuid)
        await state.set_state(UserQAStates.in_dialog)

        await callback.message.answer(
            "💬 <b>ПРОДОЛЖЕНИЕ ДИАЛОГА</b>\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text[:200]}...\n\n"
            "Напишите ваше сообщение фармацевту:\n"
            "(или /cancel для отмены)",
            parse_mode="HTML",
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in continue_user_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при продолжении диалога", show_alert=True)


@router.callback_query(F.data == "view_questions")
async def view_questions_callback(
    callback: CallbackQuery, db: AsyncSession, is_pharmacist: bool, pharmacist: object
):
    """Быстрый просмотр вопросов через кнопку"""
    if not is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    await callback.answer()

    try:
        from sqlalchemy import select
        from db.qa_models import Question, User

        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.desc())  # Новые сверху
        )
        questions = result.scalars().all()

        if not questions:
            await callback.message.answer("📝 На данный момент нет новых вопросов.\n\n")
            return

        for i, question in enumerate(questions, 1):
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
            else:
                question_text = (
                    f"❓ Вопрос #{i}:\n{question.text}\n\n"
                    f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

            # Для всех вопросов в списке - простая кнопка "Ответить"
            from bot.keyboards.qa_keyboard import make_question_list_keyboard

            reply_markup = make_question_list_keyboard(question.uuid)

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
        reply_markup=get_user_keyboard(),
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
@router.message(Command("complete"))
async def cmd_complete(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Команда для завершения консультации пользователем"""
    if is_pharmacist:
        await message.answer(
            "👨‍⚕️ Вы фармацевт. Используйте /end_dialog для завершения диалогов."
        )
        return

    try:
        # Получаем последнюю отвеченную консультацию пользователя
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid, Question.status == "answered")
            .order_by(Question.answered_at.desc())
            .limit(5)
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📭 У вас нет активных консультаций для завершения.\n\n"
                "Сначала задайте вопрос и дождитесь ответа фармацевта."
            )
            return

        # Создаем клавиатуру с консультациями для завершения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions:
            question_preview = (
                question.text[:50] + "..." if len(question.text) > 50 else question.text
            )
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"❓ {question_preview}",
                        callback_data=f"complete_consultation_{question.uuid}",
                    )
                ]
            )

        await message.answer(
            "✅ <b>Завершить консультацию</b>\n\n" "Выберите консультацию:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(f"Error in cmd_complete: {e}")
        await message.answer("❌ Ошибка при получении консультаций")


@router.message(Command("cancel"))
async def universal_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    logger.info(f"Command /cancel from user {message.from_user.id}")

    current_state = await state.get_state()

    if current_state is None:
        await message.answer("❌ Нечего отменять.")
        return

    # Очищаем состояние
    await state.clear()

    # Уведомляем пользователя
    await message.answer(
    "❌ <b>Отмена</b>\n\n"
    "Задайте новый вопрос или выберите действие.",
    parse_mode="HTML",
)


@router.callback_query(F.data == "my_questions")
async def my_questions_from_completed_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Обработка кнопки 'Мои вопросы' из завершенного диалога"""
    await callback.answer()

    # Используем существующую функцию
    from bot.handlers.user_questions import cmd_my_questions

    await cmd_my_questions(callback, db, user, is_pharmacist)


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
    callback: CallbackQuery, state: FSMContext, is_pharmacist: bool
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
        keyboard=[[KeyboardButton(text="❌ Отмена регистрации")]], resize_keyboard=True
    )

    await callback.message.answer(
        "🔐 Регистрация фармацевта\n\n"
        "Для начала регистрации введите секретное слово:",
        reply_markup=cancel_keyboard,
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
