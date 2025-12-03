from aiogram.types import Message, CallbackQuery
from typing import Union

from aiogram import Router, F

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.qa_models import User, Pharmacist
from db.qa_models import Question
from db.qa_models import Answer
from bot.handlers.qa_states import QAStates
# ИСПРАВИТЬ импорт (убрать дублирование):
from bot.keyboards.qa_keyboard import (
    make_question_keyboard,
    make_clarification_keyboard
)
from bot.services.assignment_service import QuestionAssignmentService 

from bot.handlers.common_handlers import get_pharmacist_keyboard
import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

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
    """Показать вопросы с пагинацией - ОБНОВЛЕННАЯ ВЕРСИЯ С ПРАВИЛЬНЫМИ КНОПКАМИ ДЛЯ УТОЧНЕНИЙ"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.asc())  # Сначала старые вопросы

        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
            return

        for i, question in enumerate(questions, 1):
            # Проверяем, является ли вопрос уточнением
            is_clarification = (
                question.context_data and
                question.context_data.get("is_clarification")
            )

            if is_clarification:
                original_question_id = question.context_data.get("original_question_id")
                original_question_text = question.context_data.get("original_question_text", "")

                question_text = (
                    f"🔍 <b>УТОЧНЕНИЕ К ВОПРОСУ</b>\n\n"
                    f"❓ Исходный вопрос: {original_question_text}\n\n"
                    f"💬 Уточнение: {question.text}\n\n"
                    f"🕒 Создано: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

                # Для уточнений используем специальную клавиатуру

                reply_markup = make_clarification_keyboard(question.uuid)
            else:
                question_text = (
                    f"❓ Вопрос #{i}:\n{question.text}\n\n"
                    f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
                )

                # Для обычных вопросов используем обычную клавиатуру
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

            await message.answer(
                question_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

        if len(questions) == 5:
            await message.answer(
                "💡 Показаны первые 5 вопросов. Ответьте на них чтобы увидеть следующие."
            )

    except Exception as e:
        logger.error(f"Error in cmd_questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")

# bot/handlers/qa_handlers.py - добавляем новую команду
@router.message(Command("release_question"))
async def cmd_release_question(
    message: Message,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist
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
                Question.taken_by == pharmacist.uuid,
                Question.status == "in_progress"
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
            question_preview = question.text[:50] + "..." if len(question.text) > 50 else question.text
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"📌 {question_preview}",
                    callback_data=f"release_{question.uuid}"
                )
            ])

        await message.answer(
            "📋 Выберите вопрос, который хотите освободить:",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in cmd_release_question: {e}")
        await message.answer("❌ Ошибка при получении вопросов")

@router.callback_query(F.data.startswith("release_"))
async def release_question_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist
):
    """Освободить выбранный вопрос"""
    question_uuid = callback.data.replace("release_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.taken_by != pharmacist.uuid:
            await callback.answer("❌ Вопрос не найден или не взят вами", show_alert=True)
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
    is_pharmacist: bool
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
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    try:
        # Назначаем вопрос фармацевту
        assignment_success = await QuestionAssignmentService.assign_question_to_pharmacist(
            question_uuid,
            str(pharmacist.uuid),
            db
        )

        if not assignment_success:
            await callback.answer("❌ Ошибка при назначении вопроса", show_alert=True)
            return

        # Остальная логика остается прежней...
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Сохраняем ID вопроса в состоянии
        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        question_preview = (
            question.text[:100] + "..." if len(question.text) > 100 else question.text
        )

        await callback.message.answer(
            f"💬 Вы взяли вопрос на себя!\n\n"
            f"«{question_preview}»\n\n"
            f"Напишите ваш ответ ниже:\n"
            f"(или /cancel для отмены)"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_question_callback: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)




@router.message(QAStates.waiting_for_answer)
async def process_answer_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка текста ответа на вопрос - с поддержкой уточнений"""
    logger.info(f"Processing answer from pharmacist {message.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")
        is_clarification = state_data.get("is_clarification", False)

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
            logger.info(f"Pharmacist {message.from_user.id} auto-set to online")

        # Создаем ответ
        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )

        db.add(answer)

        if is_clarification:
            # Для уточнения помечаем его как отвеченный
            question.status = "answered"
            question.answered_at = get_utc_now_naive()
        else:
            # Для обычного вопроса обновляем статус
            question.status = "answered"
            question.answered_at = get_utc_now_naive()

        await db.commit()

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

                pharmacist_name = " ".join(pharmacist_name_parts) if pharmacist_name_parts else "Фармацевт"

                pharmacist_info = f"{pharmacist_name}"
                if chain and number:
                    pharmacist_info += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info += f" ({role})"

                # СОЗДАЕМ КНОПКУ УТОЧНЕНИЯ ДЛЯ ЛЮБОГО ТИПА ВОПРОСА
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

                clarify_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✍️ Уточнить вопрос",
                                callback_data=f"quick_clarify_{question.uuid}"
                            )
                        ]
                    ]
                )

                if is_clarification:
                    # Сообщение для уточнения
                    original_question_id = question.context_data.get("original_question_id")
                    original_question_text = question.context_data.get("original_question_text", "")

                    message_text = (
                        f"💊 <b>На ваше уточнение получен ответ!</b>\n\n"
                        f"❓ <b>Исходный вопрос:</b>\n{original_question_text}\n\n"
                        f"💬 <b>Ваше уточнение:</b>\n{question.text.replace('Уточнение: ', '')}\n\n"
                        f"💬 <b>Ответ:</b>\n{message.text}\n\n"
                        f"👨‍⚕️ <b>Ответ предоставил:</b> {pharmacist_info}"
                    )
                else:
                    # Сообщение для обычного вопроса
                    message_text = (
                        f"💊 <b>На ваш вопрос получен ответ!</b>\n\n"
                        f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
                        f"💬 <b>Ответ:</b>\n{message.text}\n\n"
                        f"👨‍⚕️ <b>Ответ предоставил:</b> {pharmacist_info}\n\n"
                        f"<i>Если ответ неполный или у вас есть уточняющий вопрос, "
                        f"нажмите кнопку ниже ↓</i>"
                    )

                # ОТПРАВЛЯЕМ ВСЕГДА С КНОПКОЙ УТОЧНЕНИЯ
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=clarify_keyboard
                )

                logger.info(f"Notification sent to user {user.telegram_id} about answer")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")

        success_message = "✅ Ответ успешно отправлен пользователю!"
        if is_clarification:
            success_message = "✅ Ответ на уточнение успешно отправлен пользователю!"

        await message.answer(
            f"{success_message}\n\n"
            "Используйте /questions для просмотра других вопросов."
        )

        await state.clear()

    except Exception as e:
        logger.error(
            f"Error in process_answer_text for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке ответа")
        await state.clear()


# Добавьте этот метод в конец файла qa_handlers.py

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

    logger.info(f"Clarification answer callback for question {question_uuid} from user {callback.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await callback.answer("❌ Эта функция доступна только фармацевтам", show_alert=True)
        return

    try:
        # Получаем вопрос уточнения
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        clarification_question = result.scalar_one_or_none()

        if not clarification_question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем, что это действительно уточнение
        if not clarification_question.context_data or not clarification_question.context_data.get("is_clarification"):
            await callback.answer("❌ Это не уточнение", show_alert=True)
            return

        # Сохраняем ID вопроса уточнения в состоянии
        await state.update_data(
            question_uuid=question_uuid,
            is_clarification=True,
            original_question_id=clarification_question.context_data.get("original_question_id")
        )
        await state.set_state(QAStates.waiting_for_answer)

        original_question_text = clarification_question.context_data.get("original_question_text", "")

        await callback.message.answer(
            f"🔍 Вы отвечаете на <b>УТОЧНЕНИЕ</b>:\n\n"
            f"❓ <b>Исходный вопрос:</b>\n{original_question_text}\n\n"
            f"💬 <b>Уточнение от пользователя:</b>\n{clarification_question.text}\n\n"
            f"✍️ <b>Напишите ваш ответ ниже:</b>\n"
            f"(или /cancel для отмены)",
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_clarification_callback for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
