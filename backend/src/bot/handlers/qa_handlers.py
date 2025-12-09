# Стандартная библиотека
import logging
from datetime import datetime, timedelta
from typing import Union

# Сторонние пакеты
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Внутренние модули проекта
from utils.time_utils import get_utc_now_naive
from db.qa_models import User, Pharmacist, Question, Answer, DialogMessage
from bot.handlers.qa_states import QAStates
from bot.handlers.common_handlers import get_pharmacist_keyboard
from bot.services.dialog_service import DialogService
from bot.services.assignment_service import QuestionAssignmentService
from bot.keyboards.qa_keyboard import (
    make_question_list_keyboard,
    make_pharmacist_dialog_keyboard,
    make_user_consultation_keyboard,
    make_question_keyboard,
)

# Инициализация
logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("online"))
async def set_online(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Установка статуса онлайн для фармацевта с проверкой ожидающих вопросов"""
    logger.info(
        f"Command /online from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        logger.warning(
            f"User {message.from_user.id} is not pharmacist but tried to use /online"
        )
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    try:
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        logger.info(f"Pharmacist {message.from_user.id} successfully set online status")

        # Проверяем есть ли ожидающие вопросы
        from sqlalchemy import select, func

        result = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )
        pending_count = result.scalar() or 0

        if pending_count > 0:
            await message.answer(
                f"✅ Вы теперь онлайн и готовы принимать вопросы!\n\n"
                f"📝 <b>Ожидающих вопросов:</b> {pending_count}\n"
                f"Используйте /questions чтобы просмотреть вопросы.",
                parse_mode="HTML",
                reply_markup=get_pharmacist_keyboard(),  # Добавляем клавиатуру
            )

            # Показываем первые 3 вопроса
            result = await db.execute(
                select(Question)
                .where(Question.status == "pending")
                .order_by(Question.created_at.asc())
                .limit(3)
            )
            questions = result.scalars().all()

            for i, question in enumerate(questions, 1):
                question_preview = (
                    question.text[:100] + "..."
                    if len(question.text) > 100
                    else question.text
                )
                await message.answer(
                    f"❓ Вопрос #{i}:\n{question_preview}\n",
                    reply_markup=make_question_keyboard(question.uuid),
                )
        else:
            await message.answer(
                "✅ Вы теперь онлайн и готовы принимать вопросы!\n\n"
                "На данный момент новых вопросов нет. "
                "Вы получите уведомление, когда появится новый вопрос.",
                reply_markup=get_pharmacist_keyboard(),
            )

    except Exception as e:
        logger.error(
            f"Error setting online status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("offline"))
async def set_offline(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Установка статуса офлайн для фармацевта"""
    logger.info(
        f"Command /offline from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        logger.warning(
            f"User {message.from_user.id} is not pharmacist but tried to use /offline"
        )
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    try:
        pharmacist.is_online = False
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        logger.info(
            f"Pharmacist {message.from_user.id} successfully set offline status"  # вместо pharmacist.telegram_id
        )

        await message.answer("✅ Вы теперь офлайн.")

    except Exception as e:
        logger.error(
            f"Error setting offline status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("export_history"))
async def cmd_export_history(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool
):
    """Экспорт истории диалогов"""
    try:
        if is_pharmacist:
            result = await db.execute(
                select(Question)
                .where(Question.taken_by == user.uuid)
                .order_by(Question.created_at.desc())
                .limit(5)
            )
        else:
            result = await db.execute(
                select(Question)
                .where(Question.user_id == user.uuid)
                .order_by(Question.created_at.desc())
                .limit(5)
            )

        questions = result.scalars().all()

        if not questions:
            await message.answer("📭 У вас нет диалогов для экспорта.")
            return

        await message.answer(
            "📤 <b>Экспорт истории диалогов</b>\n\n"
            "Выберите диалог для экспорта:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"Диалог #{i+1}: {q.text[:30]}...",
                            callback_data=f"export_dialog_{q.uuid}"
                        )
                    ] for i, q in enumerate(questions[:5])
                ]
            )
        )

    except Exception as e:
        logger.error(f"Error in cmd_export_history: {e}")
        await message.answer("❌ Ошибка при экспорте истории")


@router.message(Command("status"))
async def cmd_status(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Показать статус фармацевта"""
    logger.info(
        f"Command /status from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    if not is_pharmacist or not pharmacist:
        await message.answer(
            "❌ Эта команда доступна только для зарегистрированных фармацевтов"
        )
        return

    status = "онлайн" if pharmacist.is_online else "офлайн"
    last_seen = (
        pharmacist.last_seen.strftime("%d.%m.%Y %H:%M")
        if pharmacist.last_seen
        else "никогда"
    )

    await message.answer(
        f"📊 Ваш статус:\n\n"
        f"• Статус: {status}\n"
        f"• Последняя активность: {last_seen}\n"
        f"• Зарегистрирован: {pharmacist.created_at.strftime('%d.%m.%Y')}"
    )


# В qa_handlers.py обновляем cmd_questions


@router.message(Command("questions"))
async def cmd_questions(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Показать вопросы - новые сверху"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
            return

        for i, question in enumerate(questions, 1):
            # ПРОВЕРЯЕМ ВЗЯТИЕ ВОПРОСА
            is_taken = question.taken_by is not None
            is_taken_by_me = is_taken and question.taken_by == pharmacist.uuid

            # ОПРЕДЕЛЯЕМ ФАРМАЦЕВТА, КОТОРЫЙ ВЗЯЛ ВОПРОС
            taken_by_info = ""
            if is_taken and not is_taken_by_me:
                # Получаем информацию о фармацевте
                pharmacist_result = await db.execute(
                    select(Pharmacist)
                    .where(Pharmacist.uuid == question.taken_by)
                )
                taken_pharmacist = pharmacist_result.scalar_one_or_none()

                if taken_pharmacist and taken_pharmacist.pharmacy_info:
                    # Формируем ФИО
                    first_name = taken_pharmacist.pharmacy_info.get("first_name", "")
                    last_name = taken_pharmacist.pharmacy_info.get("last_name", "")
                    patronymic = taken_pharmacist.pharmacy_info.get("patronymic", "")

                    name_parts = []
                    if last_name:
                        name_parts.append(last_name)
                    if first_name:
                        name_parts.append(first_name)
                    if patronymic:
                        name_parts.append(patronymic)

                    pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"
                    chain = taken_pharmacist.pharmacy_info.get("chain", "")
                    number = taken_pharmacist.pharmacy_info.get("number", "")

                    taken_by_info = f"\n👨‍⚕️ Взял: {pharmacist_name}"
                    if chain and number:
                        taken_by_info += f" ({chain}, аптека №{number})"

            # ФОРМИРУЕМ СООБЩЕНИЕ
            status_color = ""
            status_icon = ""
            status_text = ""

            if is_taken_by_me:
                status_color = "🟡"
                status_icon = "👤"
                status_text = "ВЗЯТ ВАМИ"
            elif is_taken:
                status_color = "🔴"
                status_icon = "⛔"
                status_text = "УЖЕ ВЗЯТ"
            else:
                status_color = "🟢"
                status_icon = "✅"
                status_text = "СВОБОДЕН"

            question_text = (
                f"{status_color} <b>{status_icon} {status_text}</b>\n"
                f"{taken_by_info}\n"
                f"⏰ Время взятия: {question.taken_at.strftime('%H:%M:%S') if question.taken_at else 'Не взято'}\n\n"
                f"❓ <b>Вопрос #{i}:</b>\n{question.text}\n\n"
                f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

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

            # СОЗДАЕМ КЛАВИАТУРУ
            reply_markup = None
            if is_taken_by_me:
                # Вопрос взят мной - можно ответить или освободить
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Ответить",
                                callback_data=f"answer_{question.uuid}"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🔄 Освободить вопрос",
                                callback_data=f"release_{question.uuid}"
                            )
                        ]
                    ]
                )
            elif not is_taken:
                # Свободный вопрос - можно взять
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Взять и ответить",
                                callback_data=f"answer_{question.uuid}"
                            )
                        ]
                    ]
                )
            else:
                # Вопрос взят другим - только просмотр
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="👀 Только просмотр",
                                callback_data=f"view_only_{question.uuid}"
                            )
                        ]
                    ]
                )

            await message.answer(
                question_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error in cmd_questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")


# bot/handlers/qa_handlers.py - добавляем новую команду
@router.message(Command("release_question"))
async def cmd_release_question(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Освободить вопрос, если не можешь ответить"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
        # Находим вопросы, взятые текущим фармацевтом
        result = await db.execute(
            select(Question)
            .where(
                Question.taken_by == pharmacist.uuid, Question.status == "in_progress"
            )
            .order_by(Question.taken_at.desc())
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer("📝 У вас нет взятых вопросов.")
            return

        # Создаем клавиатуру с вопросами для освобождения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions[:5]:  # Ограничиваем 5 вопросами
            question_preview = (
                question.text[:50] + "..." if len(question.text) > 50 else question.text
            )
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"📌 {question_preview}",
                        callback_data=f"release_{question.uuid}",
                    )
                ]
            )

        await message.answer(
            "📋 Выберите вопрос, который хотите освободить:", reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in cmd_release_question: {e}")
        await message.answer("❌ Ошибка при получении вопросов")


# В файл qa_handlers.py добавляем новые обработчики:

@router.callback_query(F.data.startswith("show_history_"))
async def show_dialog_history_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User
):
    """Показать полную историю диалога"""
    question_uuid = callback.data.replace("show_history_", "")

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question)
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем доступ
        if is_pharmacist:
            if question.taken_by != pharmacist.uuid and question.taken_by is not None:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return
        else:
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

        # Получаем отформатированную историю
        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question_uuid, db
        )

        # Отправляем историю
        await callback.message.answer(
            history_text,
            parse_mode="HTML"
        )

        # Если есть фото, отправляем их
        if file_ids:
            for file_id in file_ids:
                try:
                    await callback.message.answer_photo(
                        file_id,
                        caption="📸 Фото из истории диалога"
                    )
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")
                    await callback.message.answer(
                        "⚠️ Не удалось отправить одно из фото (файл устарел)"
                    )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_dialog_history_callback: {e}")
        await callback.answer("❌ Ошибка при загрузке истории", show_alert=True)


@router.callback_query(F.data.startswith("view_dialog_"))
async def view_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User
):
    """Просмотр диалога с историей"""
    question_uuid = callback.data.replace("view_dialog_", "")

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем доступ
        if is_pharmacist:
            if question.taken_by != pharmacist.uuid and question.taken_by is not None:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return
        else:
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

        # Получаем последние 5 сообщений для быстрого просмотра
        messages = await DialogService.get_dialog_history(question.uuid, db, limit=5)

        # Формируем сообщение
        if is_pharmacist:
            user_info = f"{question.user.first_name or 'Пользователь'}"
            if question.user.last_name:
                user_info = f"{question.user.first_name} {question.user.last_name}"
            message_text = (
                f"💬 <b>ДИАЛОГ С ПОЛЬЗОВАТЕЛЕМ</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_info}\n"
                f"❓ <b>Вопрос:</b> {question.text[:200]}...\n\n"
            )
        else:
            message_text = (
                f"💬 <b>ВАШ ДИАЛОГ С ФАРМАЦЕВТОМ</b>\n\n"
                f"❓ <b>Ваш вопрос:</b> {question.text[:200]}...\n\n"
            )

        # Добавляем последние сообщения
        if messages:
            message_text += "<b>Последние сообщения:</b>\n"
            message_text += "─" * 20 + "\n"

            for msg in reversed(messages[-3:]):  # Последние 3 сообщения
                if msg.sender_type == "user":
                    sender = "👤 Вы" if not is_pharmacist else "👤 Пользователь"
                else:
                    sender = "👨‍⚕️ Фармацевт" if is_pharmacist else "👨‍⚕️ Фармацевт"

                time_str = msg.created_at.strftime("%H:%M")

                if msg.message_type == "question":
                    preview = f"❓ {msg.text[:80]}..." if len(msg.text) > 80 else f"❓ {msg.text}"
                elif msg.message_type == "answer":
                    preview = f"💬 {msg.text[:80]}..." if len(msg.text) > 80 else f"💬 {msg.text}"
                elif msg.message_type == "clarification":
                    preview = f"🔍 {msg.text[:80]}..." if len(msg.text) > 80 else f"🔍 {msg.text}"
                elif msg.message_type == "photo":
                    preview = "📸 Фото рецепта"
                else:
                    preview = f"💭 {msg.text[:80]}..." if len(msg.text) > 80 else f"💭 {msg.text}"

                message_text += f"{sender} [{time_str}]: {preview}\n"

        # Создаем клавиатуру
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Полная история диалога",
                    callback_data=f"show_history_{question.uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Продолжить общение",
                    callback_data=f"answer_{question.uuid}"
                ) if is_pharmacist else InlineKeyboardButton(
                    text="✍️ Уточнить",
                    callback_data=f"quick_clarify_{question.uuid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить диалог",
                    callback_data=f"end_dialog_{question.uuid}"
                )
            ]
        ])

        await callback.message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при просмотре диалога", show_alert=True)



@router.callback_query(F.data.startswith("view_only_"))
async def view_only_question_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist
):
    """Просмотр вопроса, который уже взят другим фармацевтом"""
    question_uuid = callback.data.replace("view_only_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам",
            show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Получаем информацию о фармацевте, который взял вопрос
        pharmacist_info = ""
        if question.taken_by:
            pharmacist_result = await db.execute(
                select(Pharmacist)
                .where(Pharmacist.uuid == question.taken_by)
            )
            taken_pharmacist = pharmacist_result.scalar_one_or_none()

            if taken_pharmacist and taken_pharmacist.pharmacy_info:
                first_name = taken_pharmacist.pharmacy_info.get("first_name", "")
                last_name = taken_pharmacist.pharmacy_info.get("last_name", "")
                patronymic = taken_pharmacist.pharmacy_info.get("patronymic", "")

                name_parts = []
                if last_name:
                    name_parts.append(last_name)
                if first_name:
                    name_parts.append(first_name)
                if patronymic:
                    name_parts.append(patronymic)

                pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"
                chain = taken_pharmacist.pharmacy_info.get("chain", "")
                number = taken_pharmacist.pharmacy_info.get("number", "")

                pharmacist_info = f"👨‍⚕️ <b>Взял:</b> {pharmacist_name}"
                if chain and number:
                    pharmacist_info += f" ({chain}, аптека №{number})"
                if question.taken_at:
                    pharmacist_info += f"\n⏰ <b>Время взятия:</b> {question.taken_at.strftime('%H:%M:%S')}"

        # Формируем сообщение
        message_text = (
            f"🔴 <b>ВОПРОС УЖЕ ВЗЯТ ДРУГИМ ФАРМАЦЕВТОМ</b>\n\n"
            f"{pharmacist_info}\n\n"
            f"❓ <b>Вопрос:</b>\n{question.text}\n\n"
            f"🕒 <b>Создан:</b> {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 <b>Статус:</b> В работе другим фармацевтом"
        )

        await callback.message.answer(
            message_text,
            parse_mode="HTML"
        )

        await callback.answer("Этот вопрос уже взят другим фармацевтом")

    except Exception as e:
        logger.error(f"Error in view_only_question_callback: {e}")
        await callback.answer("❌ Ошибка при просмотре вопроса", show_alert=True)

@router.callback_query(F.data.startswith("release_"))
async def release_question_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Освободить выбранный вопрос"""
    question_uuid = callback.data.replace("release_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.taken_by != pharmacist.uuid:
            await callback.answer(
                "❌ Вопрос не найден или не взят вами", show_alert=True
            )
            return

        # Освобождаем вопрос
        question.taken_by = None
        question.taken_at = None
        question.status = "pending"

        await db.commit()

        await callback.answer("✅ Вопрос освобожден!")
        await callback.message.edit_text(
            f"✅ Вопрос освобожден.\n\n"
            f"❓ Вопрос: {question.text[:100]}...\n\n"
            f"Теперь его смогут взять другие фармацевты."
        )

    except Exception as e:
        logger.error(f"Error releasing question: {e}")
        await callback.answer("❌ Ошибка при освобождении вопроса", show_alert=True)


@router.message(Command("debug_status"))
@router.callback_query(F.data == "debug_status")  # Добавляем поддержку callback
async def debug_status(
    message_or_callback: Union[Message, CallbackQuery],
    db: AsyncSession,
    is_pharmacist: bool,
):
    """Команда для отладки статуса системы"""
    # Определяем, что пришло: Message или CallbackQuery
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
        from_user = message_or_callback.from_user
    else:
        message = message_or_callback
        from_user = message.from_user

    try:
        from sqlalchemy import select, func
        from bot.services.notification_service import get_online_pharmacists

        # Статистика по вопросам
        total_questions = await db.execute(select(func.count(Question.uuid)))
        pending_questions = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )

        # Онлайн фармацевты
        online_pharmacists = await get_online_pharmacists(db)

        # Все активные фармацевты
        all_pharmacists_result = await db.execute(
            select(Pharmacist).where(Pharmacist.is_active == True)
        )
        all_pharmacists = all_pharmacists_result.scalars().all()

        status_text = (
            f"🔧 <b>Отладочная информация системы</b>\n\n"
            f"📊 <b>Вопросы:</b>\n"
            f"• Всего: {total_questions.scalar()}\n"
            f"• Ожидают ответа: {pending_questions.scalar()}\n\n"
            f"👨‍⚕️ <b>Фармацевты:</b>\n"
            f"• Всего активных: {len(all_pharmacists)}\n"
            f"• Сейчас онлайн: {len(online_pharmacists)}\n\n"
            f"🕒 <b>Время сервера:</b>\n"
            f"{get_utc_now_naive().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Детальная информация об онлайн фармацевтах
        if online_pharmacists:
            status_text += f"\n\n<b>Онлайн фармацевты:</b>"
            for i, pharm in enumerate(online_pharmacists, 1):
                last_seen = (
                    pharm.last_seen.strftime("%H:%M:%S")
                    if pharm.last_seen
                    else "никогда"
                )
                status_text += f"\n{i}. ID: {pharm.user.telegram_id}, Последняя активность: {last_seen}"

        await message.answer(status_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in debug_status: {e}")
        await message.answer("❌ Ошибка при получении статуса системы")


# bot/handlers/qa_handlers.py - обновляем answer_question_callback
# В функции answer_question_callback добавляем сохранение фармацевта
@router.callback_query(F.data.startswith("answer_"))
async def answer_question_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка нажатия на кнопку ответа на вопрос"""
    question_uuid = callback.data.replace("answer_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Если вопрос еще не взят, берем его
        if question.status == "pending" or question.taken_by != pharmacist.uuid:
            # Назначаем вопрос фармацевту
            assignment_success = (
                await QuestionAssignmentService.assign_question_to_pharmacist(
                    question_uuid, str(pharmacist.uuid), db
                )
            )
            await state.update_data(
                question_uuid=question_uuid, dialog_partner_id=str(pharmacist.uuid)
            )
            await state.set_state(QAStates.in_dialog_with_user)

            if not assignment_success:
                await callback.answer(
                    "❌ Ошибка при назначении вопроса", show_alert=True
                )
                return

            # Обновляем информацию о взятии
            question.taken_by = pharmacist.uuid
            question.taken_at = get_utc_now_naive()
            question.status = "in_progress"
            await db.commit()

        # Сохраняем ID вопроса в состоянии
        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        question_preview = (
            question.text[:300] + "..." if len(question.text) > 300 else question.text
        )

        # Показываем фармацевту диалоговую клавиатуру
        await callback.message.answer(
            f"💬 <b>Вы в диалоге с пользователем</b>\n\n"
            f"❓ Вопрос: {question_preview}\n\n"
            f"Напишите ваш ответ или уточняющий вопрос:\n"
            f"(или нажмите кнопки ниже для других действий)",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_question_callback: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(QAStates.in_dialog_with_user)
async def continue_dialog_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Продолжение диалога - показываем историю и кнопки"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        # Получаем полную историю диалога
        history_text, _ = await DialogService.format_dialog_history_for_display(
            question.uuid, db
        )

        # Показываем историю С КНОПКАМИ
        await message.answer(
            f"💬 <b>ТЕКУЩИЙ ДИАЛОГ</b>\n\n"
            f"{history_text}\n\n"
            f"✍️ <b>Напишите ваш следующий ответ:</b>",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question.uuid)
        )

        # Сохраняем текст для ответа
        await state.update_data(answer_text=message.text)
        await state.set_state(QAStates.waiting_for_answer)

    except Exception as e:
        logger.error(f"Error continuing dialog: {e}")
        await message.answer("❌ Ошибка при получении истории диалога")
        await state.clear()

@router.message(QAStates.waiting_for_answer)
async def process_answer_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка сообщения от фармацевта (ответ или уточнение)"""
    logger.info(f"Processing message from pharmacist {message.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        # Автоматически переводим фармацевта в онлайн при активности
        if not pharmacist.is_online:
            pharmacist.is_online = True
            pharmacist.last_seen = get_utc_now_naive()
            await db.commit()

        # ✅ ЛОГИРОВАНИЕ: Отслеживаем создание ответа
        logger.info(f"Creating answer for question {question.uuid} by pharmacist {pharmacist.uuid}")
        logger.info(f"Answer text: '{message.text}'")

        # Создаем ответ/сообщение
        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )

        db.add(answer)

        if question.status != "completed":
            question.status = "answered"
        question.answered_at = get_utc_now_naive()
        question.answered_by = pharmacist.uuid

        # ✅ ВАЖНО: Добавляем сообщение в историю диалога
        dialog_message = await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="pharmacist",
            sender_id=pharmacist.uuid,
            message_type="answer",
            text=message.text,
        )

        # ✅ ЛОГИРОВАНИЕ: Отслеживаем создание сообщения в диалоге
        logger.info(f"Dialog message created: {dialog_message.uuid}, type={dialog_message.message_type}")

        await db.commit()

        # ✅ Получаем полную историю диалога для отправки
        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question.uuid, db, limit=20
        )

        # ✅ ЛОГИРОВАНИЕ: Отслеживаем сформированную историю
        logger.info(f"History text length: {len(history_text)}")
        logger.info(f"History text preview: {history_text[:200]}...")

        # Уведомляем пользователя
        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            try:
                # Формируем информацию о фармацевте с ФИО
                pharmacy_info = pharmacist.pharmacy_info or {}
                chain = pharmacy_info.get("chain", "Не указана")
                number = pharmacy_info.get("number", "Не указан")
                role = pharmacy_info.get("role", "Фармацевт")

                # Получаем ФИО фармацевта
                first_name = pharmacy_info.get("first_name", "")
                last_name = pharmacy_info.get("last_name", "")
                patronymic = pharmacy_info.get("patronymic", "")

                # Формируем строку с ФИО
                pharmacist_name_parts = []
                if last_name:
                    pharmacist_name_parts.append(last_name)
                if first_name:
                    pharmacist_name_parts.append(first_name)
                if patronymic:
                    pharmacist_name_parts.append(patronymic)

                pharmacist_name = (
                    " ".join(pharmacist_name_parts)
                    if pharmacist_name_parts
                    else "Фармацевт"
                )

                pharmacist_info_text = f"{pharmacist_name}"
                if chain and number:
                    pharmacist_info_text += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info_text += f" ({role})"

                # Формируем полное сообщение с историей
                full_message = (
                    f"💬 <b>ОТВЕТ ФАРМАЦЕВТА</b>\n\n"
                    f"{history_text}\n\n"
                    f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_info_text}"
                )

                # Отправляем сообщение пользователю С КНОПКАМИ
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=full_message,
                    parse_mode="HTML",
                    reply_markup=make_user_consultation_keyboard(question.uuid)
                )

                logger.info(f"Message sent to user {user.telegram_id}")

            except Exception as e:
                logger.error(f"Failed to send message to user {user.telegram_id}: {e}", exc_info=True)

        # ✅ Показываем фармацевту полную историю диалога С КНОПКАМИ
        await message.answer(
            f"💬 <b>ВЫ ОТПРАВИЛИ ОТВЕТ</b>\n\n"
            f"{history_text}\n\n"
            f"<b>Доступные действия:</b>",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question.uuid)
        )

        # НЕ очищаем состояние фармацевта - оставляем в диалоге
        await state.set_state(QAStates.in_dialog_with_user)

    except Exception as e:
        logger.error(
            f"Error in process_answer_text for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке сообщения")
        await state.clear()

@router.callback_query(F.data.startswith("clarification_answer_"))
async def answer_clarification_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка нажатия на кнопку ответа на уточнение"""
    question_uuid = callback.data.replace("clarification_answer_", "")

    logger.info(
        f"Clarification answer callback for question {question_uuid} from user {callback.from_user.id}"
    )

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # ✅ ОБНОВЛЕНО: Проверяем, есть ли у этого вопроса уточнения или он был отвечен
        # Получаем последний ответ для контекста
        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        if not last_answer and question.status != "answered":
            await callback.answer("❌ На этот вопрос еще нет ответа", show_alert=True)
            return

        # Сохраняем ID вопроса в состоянии
        await state.update_data(
            question_uuid=question_uuid,
            is_clarification=True,
        )
        await state.set_state(QAStates.waiting_for_answer)

        await callback.message.answer(
            f"🔍 Вы отвечаете на <b>УТОЧНЕНИЕ</b>:\n\n"
            f"❓ <b>Вопрос:</b>\n{question.text}\n\n"
            f"💬 <b>Предыдущий ответ:</b>\n{last_answer.text if last_answer else 'Нет предыдущих ответов'}\n\n"
            f"✍️ <b>Напишите ваш ответ на уточнение ниже:</b>\n"
            f"(или /cancel для отмены)",
            parse_mode="HTML",
        )

        await callback.answer()

    except Exception as e:
        logger.error(
            f"Error in answer_clarification_callback for user {callback.from_user.id}: {e}",
            exc_info=True,
        )
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


# В файл qa_handlers.py добавить


# В файл qa_handlers.py, в функцию request_photo_callback добавить:
@router.callback_query(F.data.startswith("request_photo_"))
async def request_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка запроса фото рецепта от фармацевта"""
    question_uuid = callback.data.replace("request_photo_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем, взят ли вопрос этим фармацевтом
        if question.taken_by != pharmacist.uuid and question.status == "in_progress":
            await callback.answer(
                "❌ Этот вопрос уже взят другим фармацевтом", show_alert=True
            )
            return

        # Если вопрос еще не взят, берем его
        if question.status == "pending":
            question.taken_by = pharmacist.uuid
            question.taken_at = get_utc_now_naive()
            question.status = "in_progress"

        # Сохраняем информацию о запросе фото
        if not question.context_data:
            question.context_data = {}

        question.context_data["photo_requested_by"] = {
            "pharmacist_id": str(pharmacist.uuid),
            "telegram_id": pharmacist.user.telegram_id,
            "requested_at": get_utc_now_naive().isoformat(),
        }
        question.context_data["photo_requested"] = True

        await db.commit()

        # Сохраняем ID вопроса в состоянии для продолжения диалога
        await state.update_data(question_uuid=question_uuid)

        # Уведомляем фармацевта
        await callback.answer("✅ Запрос фото отправлен пользователю!")

        await callback.message.answer(
            f"📸 <b>Запрос фото рецепта отправлен</b>\n\n"
            f"Пользователь получил уведомление о необходимости отправить фото.\n\n"
            f"Продолжайте диалог:",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )

    except Exception as e:
        logger.error(f"Error in request_photo_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.callback_query(F.data.startswith("request_more_photos_"))
async def request_more_photos_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Запросить еще фото рецепта"""
    question_uuid = callback.data.replace("request_more_photos_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Сохраняем информацию о запросе дополнительного фото
        if not question.context_data:
            question.context_data = {}

        question.context_data["photo_requested_by"] = {
            "pharmacist_id": str(pharmacist.uuid),
            "telegram_id": pharmacist.user.telegram_id,
            "requested_at": get_utc_now_naive().isoformat(),
        }
        question.context_data["photo_requested"] = True

        await db.commit()

        # Создаем клавиатуру для отправки фото
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        photo_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📸 Отправить еще фото рецепта",
                        callback_data=f"send_prescription_photo_{question.uuid}",
                    )
                ]
            ]
        )

        # Отправляем запрос пользователю
        await callback.bot.send_message(
            chat_id=question.user.telegram_id,
            text=f"📸 <b>Фармацевт запросил дополнительное фото рецепта</b>\n\n"
            f"❓ <b>По вопросу:</b>\n{question.text}\n\n"
            f"Пожалуйста, отправьте еще фото рецепта:",
            parse_mode="HTML",
            reply_markup=photo_keyboard,
        )

        await callback.answer("✅ Запрос на дополнительное фото отправлен пользователю!")

        # Продолжаем диалог
        await callback.message.answer(
            "📸 Запрос на дополнительное фото отправлен пользователю.\n\n"
            "Продолжайте диалог:",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )

    except Exception as e:
        logger.error(f"Error in request_more_photos_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)

@router.message(QAStates.waiting_for_photo_request)
async def process_photo_request_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка сообщения для запроса фото рецепта"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("photo_request_question_id")
        original_message_id = state_data.get("photo_request_message_id")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос")
            await state.clear()
            return

        # Получаем вопрос и пользователя
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        # В process_photo_request_message, после получения вопроса:
        if not question or not question.user:
            await message.answer("❌ Вопрос или пользователь не найдены")
            await state.clear()
            return

        # Устанавливаем флаг, что фото запрошено
        if not question.context_data:
            question.context_data = {}
        question.context_data["photo_requested"] = True
        await db.commit()

        # Если это уточнение, также обновляем исходный вопрос (для контекста)
        if question.context_data and question.context_data.get("is_clarification"):
            original_question_id = question.context_data.get("original_question_id")
            if original_question_id:
                # Обновляем исходный вопрос тоже
                original_result = await db.execute(
                    select(Question).where(Question.uuid == original_question_id)
                )
                original_question = original_result.scalar_one_or_none()
                if original_question:
                    if not original_question.context_data:
                        original_question.context_data = {}
                    original_question.context_data["photo_requested_by"] = {
                        "pharmacist_id": str(pharmacist.uuid),
                        "telegram_id": pharmacist.user.telegram_id,
                        "requested_at": get_utc_now_naive().isoformat(),
                    }
                    original_question.context_data["photo_requested"] = True
                await db.commit()

        # ... остальной код функции остается без изменений ...

        # Формируем сообщение с ФИО фармацевта
        pharmacy_info = pharmacist.pharmacy_info or {}
        first_name = pharmacy_info.get("first_name", "")
        last_name = pharmacy_info.get("last_name", "")
        patronymic = pharmacy_info.get("patronymic", "")

        pharmacist_name_parts = []
        if last_name:
            pharmacist_name_parts.append(last_name)
        if first_name:
            pharmacist_name_parts.append(first_name)
        if patronymic:
            pharmacist_name_parts.append(patronymic)

        pharmacist_name = (
            " ".join(pharmacist_name_parts) if pharmacist_name_parts else "Фармацевт"
        )

        # Создаем клавиатуру для отправки фото
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        photo_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📸 Отправить фото рецепта",
                        callback_data=f"send_prescription_photo_{question.uuid}",
                    )
                ]
            ]
        )

        # Отправляем запрос пользователю
        await message.bot.send_message(
            chat_id=question.user.telegram_id,
            text=f"📸 <b>Фармацевт запросил фото рецепта</b>\n\n"
            f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_name}\n\n"
            f"💬 <b>Сообщение:</b>\n{message.text}\n\n"
            f"❓ <b>По вопросу:</b>\n{question.text}\n\n"
            f"Нажмите кнопку ниже, чтобы отправить фото рецепта:",
            parse_mode="HTML",
            reply_markup=photo_keyboard,
        )

        # Уведомляем фармацевта
        await message.answer(
            "✅ Запрос на фото рецепта отправлен пользователю!\n\n"
            "Вы получите уведомление, когда пользователь отправит фото."
        )

        # Редактируем оригинальное сообщение (убираем кнопку запроса фото)
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=original_message_id,
                reply_markup=None,
            )
        except:
            pass

        await state.clear()

    except Exception as e:
        logger.error(f"Error in process_photo_request_message: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке запроса")
        await state.clear()
