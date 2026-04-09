"""Обработчики команд фармацевта: /online, /offline, /status, /questions, /export_history, /release_question, /debug_status."""

import logging

from aiogram import F, Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from utils.time_utils import get_utc_now_naive
from db.qa_models import User, Pharmacist, Question, Answer
from bot.handlers.common_handlers import get_pharmacist_inline_keyboard
from bot.keyboards.qa_keyboard import make_question_keyboard
from bot.services.dialog_service import DialogService
from bot.services.notification_service import get_online_pharmacists

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

        result = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )
        pending_count = result.scalar() or 0

        if pending_count > 0:
            await message.answer(
                f"🟢 <b>Вы теперь онлайн!</b>\n\n"
                f"Ожидающих вопросов: {pending_count}\n"
                "Как придет уведомление — нажмите «💬 Ответить»",
                parse_mode="HTML",
                reply_markup=get_pharmacist_inline_keyboard(),
            )

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
                "🟢 <b>Вы теперь онлайн!</b>\n\n"
                "Как только пользователь задаст вопрос — вы получите уведомление.",
                reply_markup=get_pharmacist_inline_keyboard(),
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
            f"Pharmacist {message.from_user.id} successfully set offline status"
        )

        await message.answer(
            "✅ Вы теперь офлайн.",
            parse_mode="HTML",
            reply_markup=get_pharmacist_inline_keyboard(),
        )

    except Exception as e:
        logger.error(
            f"Error setting offline status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("export_history"))
async def cmd_export_history(
    message: Message, db: AsyncSession, user: User, is_pharmacist: bool
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
            "📤 <b>Экспорт истории диалогов</b>\n\n" "Выберите диалог для экспорта:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"Диалог #{i+1}: {q.text[:30]}...",
                            callback_data=f"export_dialog_{q.uuid}",
                        )
                    ]
                    for i, q in enumerate(questions[:5])
                ]
            ),
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
                "📝 <b>Нет новых вопросов</b>\n\n"
                "Как только пользователь задаст вопрос — вы получите уведомление.",
                parse_mode="HTML",
            )
            return

        for i, question in enumerate(questions, 1):
            is_taken = question.taken_by is not None
            is_taken_by_me = is_taken and question.taken_by == pharmacist.uuid

            taken_by_info = ""
            if is_taken and not is_taken_by_me:
                pharmacist_result = await db.execute(
                    select(Pharmacist).where(Pharmacist.uuid == question.taken_by)
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

                    pharmacist_name = (
                        " ".join(name_parts) if name_parts else "Фармацевт"
                    )
                    chain = taken_pharmacist.pharmacy_info.get("chain", "")
                    number = taken_pharmacist.pharmacy_info.get("number", "")

                    taken_by_info = f"\n👨‍⚕️ Взял: {pharmacist_name}"
                    if chain and number:
                        taken_by_info += f" ({chain}, аптека №{number})"

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

            user_result = await db.execute(
                select(User).where(User.uuid == question.user_id)
            )
            user = user_result.scalar_one_or_none()

            if user:
                user_info = user.first_name or user.telegram_username or "Аноним"
                if user.last_name:
                    user_info = f"{user.first_name} {user.last_name}"
                question_text += f"\n👤 Пользователь: {user_info}"

            reply_markup = None
            if is_taken_by_me:
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Ответить",
                                callback_data=f"answer_{question.uuid}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🔄 Освободить вопрос",
                                callback_data=f"release_{question.uuid}",
                            )
                        ],
                    ]
                )
            elif not is_taken:
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Взять и ответить",
                                callback_data=f"answer_{question.uuid}",
                            )
                        ]
                    ]
                )
            else:
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="👀 Только просмотр",
                                callback_data=f"view_only_{question.uuid}",
                            )
                        ]
                    ]
                )

            await message.answer(
                question_text, parse_mode="HTML", reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error in cmd_questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")


@router.message(Command("release_question"))
async def cmd_release_question(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: Pharmacist
):
    """Освободить вопрос, если не можешь ответить"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
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

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions[:5]:
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


@router.message(Command("debug_status"))
@router.callback_query(F.data == "debug_status")
async def debug_status(
    message_or_callback,
    db: AsyncSession,
    is_pharmacist: bool,
):
    """Команда для отладки статуса системы"""
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    try:
        total_questions = await db.execute(select(func.count(Question.uuid)))
        pending_questions = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )

        online_pharmacists = await get_online_pharmacists(db)

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
