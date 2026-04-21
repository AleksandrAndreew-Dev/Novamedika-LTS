"""Команды общего назначения: /start, /help, /history, /continue, /cancel, /complete, /search, /hide_keyboard."""

import logging

from aiogram import F, Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.qa_models import User, Question, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers.keyboards import (
    get_pharmacist_inline_keyboard,
    get_user_inline_keyboard,
    get_webapp_only_keyboard,
)
from bot.handlers.direct_questions import try_create_question
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("hide_keyboard"))
async def hide_keyboard(message: Message):
    """Скрыть reply-клавиатуру"""
    await message.answer(
        "⌨️ Клавиатура скрыта. Используйте /search чтобы вернуть.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("history"))
async def cmd_history(
    message: Message, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Показать историю всех диалогов"""
    try:
        if is_pharmacist:
            result = await db.execute(
                select(Question)
                .where(Question.taken_by == user.uuid)
                .order_by(Question.taken_at.desc())
                .limit(20)
            )
        else:
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
        status_text = "🟢 Онлайн" if pharmacist.is_online else "🔴 Офлайн"
        pharmacy_name = pharmacist.pharmacy_info.get("name", "Не указана")

        await message.answer(
            f"👨‍⚕️ <b>Панель фармацевта</b>\n\n"
            f"🏥 {pharmacy_name}\n"
            f"📊 Статус: {status_text}\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_pharmacist_inline_keyboard(),
        )
    else:
        full_message_text = (
            "👋 <b>Лучше спросите в аптеке!</b>\n\n"
            "💊 <b>Консультация профессионального фармацевта</b>\n\n"
            "Просто напишите в чат, например:\n"
            '<i>"Что можно принять от головной боли?"</i>\n\n'
            "Или выберите действие:"
        )

        await message.answer(
            full_message_text,
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )


@router.message(Command("search"))
async def show_search_webapp_command(message: Message, is_pharmacist: bool):
    """Обработка текстовой команды /search"""
    if is_pharmacist:
        await message.answer("🔍 Используйте /questions для работы с вопросами")
        return

    await message.answer(
        "🔍 Нажмите кнопку ниже для поиска лекарств:",
        reply_markup=get_webapp_only_keyboard(),
    )


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

        await state.update_data(active_dialog_question_id=str(question.uuid))
        await state.set_state(UserQAStates.in_dialog)

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
            reply_markup=get_pharmacist_inline_keyboard(),
        )
    else:
        await message.answer(
            "💬 <b>Как задать вопрос?</b>\n\n"
            "Просто напишите в чат, например:\n"
            '<i>"Что можно принять от температуры?"</i>\n\n'
            "⏳ <b>Что дальше?</b>\n"
            "Фармацевт ответит, как только освободится.\n\n"
            "👨‍⚕️ <b>Если вы фармацевт</b> — нажмите «Я фармацевт / Регистрация» в главном меню.",
            parse_mode="HTML",
            reply_markup=get_user_inline_keyboard(),
        )


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

    await state.clear()

    await message.answer(
        "❌ <b>Отмена</b>\n\n" "Задайте новый вопрос или выберите действие.",
        parse_mode="HTML",
    )


@router.message(Command("privacy"))
async def cmd_privacy(message: Message, is_pharmacist: bool):
    """Показать политику конфиденциальности"""
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

    # Добавляем кнопку для перехода на полную версию
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

    await message.answer(privacy_text, parse_mode="HTML", reply_markup=keyboard)


@router.message(F.text & ~F.command)
async def unknown_command(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Обработка текста — сначала пытаемся создать вопрос, иначе ошибка"""
    logger.info(
        f"unknown_command handler triggered for user {user.telegram_id}, text: '{message.text[:50]}'"
    )

    handled = await try_create_question(message, db, user, is_pharmacist, state)
    if not handled:
        logger.info(f"try_create_question returned False for user {user.telegram_id}")
        await message.answer(
            "❓ Неизвестная команда.\n\n"
            "Используйте /start для главного меню или /help для справки.",
        )
    else:
        logger.info(f"try_create_question handled message for user {user.telegram_id}")
