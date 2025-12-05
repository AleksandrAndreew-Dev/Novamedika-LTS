# bot/handlers/qa_handlers.py - исправленный импорт
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from typing import Union

from aiogram import Router, F

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from db.qa_models import User, Pharmacist, Question, Answer
from bot.handlers.qa_states import QAStates

# ИСПРАВЛЕННЫЙ импорт:
from bot.keyboards.qa_keyboard import (
    make_question_list_keyboard,      # НОВОЕ
    make_pharmacist_dialog_keyboard,  # НОВОЕ
    make_user_response_keyboard,
    make_user_dialog_keyboard      # НОВОЕ
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
            .order_by(Question.created_at.desc())  # Новые сверху
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
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

            await message.answer(
                question_text, parse_mode="HTML", reply_markup=reply_markup
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



@router.callback_query(F.data.startswith("complete_"))
async def complete_question_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    state: FSMContext,  # Добавляем state для очистки
):
    """Завершение вопроса фармацевтом"""
    question_uuid = callback.data.replace("complete_", "")

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

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем, взят ли вопрос этим фармацевтом
        if question.taken_by != pharmacist.uuid:
            await callback.answer(
                "❌ Вы не брали этот вопрос", show_alert=True
            )
            return

        # Завершаем вопрос
        question.status = "answered"
        question.answered_at = get_utc_now_naive()

        await db.commit()

        # Очищаем состояние фармацевта
        await state.clear()

        await callback.answer("✅ Вопрос завершен!")

        # Редактируем последнее сообщение или отправляем новое
        await callback.message.answer(
            f"✅ <b>Вопрос завершен</b>\n\n"
            f"❓ Вопрос: {question.text[:200]}...\n\n"
            f"💬 Диалог завершен. Пользователь уведомлен.\n\n"
            f"Используйте /questions для просмотра других вопросов."
        )

    except Exception as e:
        logger.error(f"Error completing question: {e}")
        await callback.answer("❌ Ошибка при завершении вопроса", show_alert=True)

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




# В qa_handlers.py добавить новые обработчики

@router.callback_query(F.data.startswith("answer_after_photo_"))
async def answer_after_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Продолжить диалог после получения фото"""
    question_uuid = callback.data.replace("answer_after_photo_", "")

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

        # Проверяем, что вопрос взят этим фармацевтом
        if question.taken_by != pharmacist.uuid and question.status == "in_progress":
            await callback.answer(
                "❌ Этот вопрос уже взят другим фармацевтом", show_alert=True
            )
            return

        # Сохраняем ID вопроса в состоянии для продолжения диалога
        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        await callback.message.answer(
            f"💬 <b>Продолжение консультации после фото</b>\n\n"
            f"❓ Вопрос: {question.text[:200]}...\n\n"
            f"Напишите дополнительный ответ или уточнение пользователю:\n"
            f"(или /cancel для отмены)",
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_after_photo_callback: {e}")
        await callback.answer("❌ Ошибка при продолжении диалога", show_alert=True)

@router.callback_query(F.data.startswith("request_more_photos_"))
async def request_more_photos_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Запросить дополнительные фото"""
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

        if not question or not question.user:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Создаем клавиатуру для пользователя
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        photo_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📸 Отправить дополнительное фото",
                        callback_data=f"send_prescription_photo_{question.uuid}",
                    )
                ]
            ]
        )

        # Отправляем запрос пользователю
        await callback.bot.send_message(
            chat_id=question.user.telegram_id,
            text=f"📸 <b>Фармацевт запросил дополнительные фото</b>\n\n"
                 f"Пожалуйста, отправьте еще фото рецепта для более точной консультации.",
            parse_mode="HTML",
            reply_markup=photo_keyboard
        )

        await callback.answer("✅ Запрос на дополнительные фото отправлен пользователю")

    except Exception as e:
        logger.error(f"Error in request_more_photos_callback: {e}")
        await callback.answer("❌ Ошибка при запросе фото", show_alert=True)

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

            if not assignment_success:
                await callback.answer("❌ Ошибка при назначении вопроса", show_alert=True)
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
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid)
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_question_callback: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


# В qa_handlers.py обновляем process_answer_text

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

        # Создаем ответ/сообщение
        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )

        db.add(answer)
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

                pharmacist_name = (
                    " ".join(pharmacist_name_parts)
                    if pharmacist_name_parts
                    else "Фармацевт"
                )

                pharmacist_info = f"{pharmacist_name}"
                if chain and number:
                    pharmacist_info += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info += f" ({role})"

                # Проверяем, запрашивал ли фармацевт фото
                photo_requested = False
                if question.context_data and "photo_requested_by" in question.context_data:
                    photo_requested = True

                # Формируем сообщение для пользователя
                message_text = (
                    f"💊 <b>Сообщение от фармацевта</b>\n\n"
                    f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_info}\n\n"
                    f"💬 <b>Сообщение:</b>\n{message.text}\n\n"
                )

                if photo_requested:
                    message_text += f"📸 <i>Фармацевт запросил фото рецепта</i>"

                # Отправляем сообщение пользователю с клавиатурой
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=make_user_dialog_keyboard(question.uuid, photo_requested)
                )

                logger.info(f"Message sent to user {user.telegram_id}")

            except Exception as e:
                logger.error(f"Failed to send message to user {user.telegram_id}: {e}")

        # Уведомляем фармацевта и снова показываем клавиатуру диалога
        await message.answer(
            f"✅ Сообщение отправлено пользователю!\n\n"
            f"💬 <b>Ваше сообщение:</b>\n{message.text[:200]}...\n\n"
            f"Продолжайте диалог или используйте другие действия:",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid)
        )

        # НЕ очищаем состояние - фармацевт может продолжать диалог

    except Exception as e:
        logger.error(
            f"Error in process_answer_text for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке сообщения")
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

    logger.info(
        f"Clarification answer callback for question {question_uuid} from user {callback.from_user.id}"
    )

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
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
        if (
            not clarification_question.context_data
            or not clarification_question.context_data.get("is_clarification")
        ):
            await callback.answer("❌ Это не уточнение", show_alert=True)
            return

        # Сохраняем ID вопроса уточнения в состоянии
        await state.update_data(
            question_uuid=question_uuid,
            is_clarification=True,
            original_question_id=clarification_question.context_data.get(
                "original_question_id"
            ),
        )
        await state.set_state(QAStates.waiting_for_answer)

        original_question_text = clarification_question.context_data.get(
            "original_question_text", ""
        )

        await callback.message.answer(
            f"🔍 Вы отвечаете на <b>УТОЧНЕНИЕ</b>:\n\n"
            f"❓ <b>Исходный вопрос:</b>\n{original_question_text}\n\n"
            f"💬 <b>Уточнение от пользователя:</b>\n{clarification_question.text}\n\n"
            f"✍️ <b>Напишите ваш ответ ниже:</b>\n"
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
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid)
        )

    except Exception as e:
        logger.error(f"Error in request_photo_callback: {e}", exc_info=True)
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
