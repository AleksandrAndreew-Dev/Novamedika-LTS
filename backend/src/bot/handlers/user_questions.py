from aiogram.types import Message as AiogramMessage
from typing import Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from db.qa_models import User, Question, Answer, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers import get_user_keyboard

from bot.services.notification_service import notify_about_clarification


import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive
from bot.services.dialog_service import DialogService

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("ask"))
async def cmd_ask(message: Message):
    """Быстрая команда для вопроса"""
    await message.answer(
        "📝 <b>Просто напишите ваш вопрос в чат!</b>\n\n"
        "Не нужно нажимать кнопки или писать команды — просто опишите вашу проблему.\n\n"
        "<i>Пишите прямо здесь ↓</i>",
        parse_mode="HTML",
    )


# В user_questions.py обновляем cmd_my_questions:

@router.message(Command("my_questions"))
@router.callback_query(F.data == "my_questions_callback")
async def cmd_my_questions(
    update: Union[Message, CallbackQuery],
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Показать вопросы пользователя или ответы фармацевта"""
    if isinstance(update, CallbackQuery):
        message = update.message
        from_user = update.from_user
        is_callback = True
    else:
        message = update
        from_user = update.from_user
        is_callback = False

    try:
        if is_pharmacist:
            # Для фармацевтов - активные диалоги
            result = await db.execute(
                select(Question)
                .where(
                    Question.taken_by == user.uuid,
                    Question.status.in_(["in_progress", "answered"])
                )
                .order_by(Question.taken_at.desc())
            )
            questions = result.scalars().all()
        else:
            # Для пользователей - вопросы со статусом answered или in_progress
            result = await db.execute(
                select(Question)
                .where(
                    Question.user_id == user.uuid,
                    Question.status.in_(["in_progress", "answered"])
                )
                .order_by(Question.created_at.desc())
            )
            questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📭 У вас нет активных диалогов.\n\n"
                "Начните новый диалог, отправив вопрос в чат."
            )
            if is_callback:
                await update.answer()
            return

        # Создаем клавиатуру с диалогами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for i, question in enumerate(questions[:10], 1):  # Ограничиваем 10 диалогами
            status_icon = "💬" if question.status == "answered" else "🔄"
            question_preview = question.text[:50] + "..." if len(question.text) > 50 else question.text

            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_icon} Диалог #{i}: {question_preview}",
                    callback_data=f"view_dialog_{question.uuid}"
                )
            ])

        # Добавляем кнопку для всех завершенных диалогов
        if is_pharmacist:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text="📚 Все мои ответы",
                    callback_data="all_my_answers"
                )
            ])
        else:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text="📚 Архив завершенных консультаций",
                    callback_data="completed_consultations"
                )
            ])

        await message.answer(
            f"💬 <b>ВАШИ АКТИВНЫЕ ДИАЛОГИ</b>\n\n"
            f"Всего активных диалогов: {len(questions)}\n\n"
            f"Выберите диалог для просмотра истории:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        if is_callback:
            await update.answer()

    except Exception as e:
        logger.error(f"Error in cmd_my_questions: {e}")
        await message.answer("❌ Ошибка при получении диалогов")


@router.message(Command("done"))
async def cmd_done(
    message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool
):
    """Завершение диалога"""
    logger.info(
        f"Command /done from user {message.from_user.id}, is_pharmacist: {is_pharmacist}"
    )

    current_state = await state.get_state()

    if current_state == UserQAStates.in_dialog:
        await state.clear()
        await message.answer(
            "✅ Диалог завершен.\n\n" "Если у вас есть еще вопросы, используйте /ask"
        )
    else:
        await message.answer("ℹ️ В данный момент у вас нет активного диалога.")


# bot/handlers/user_questions.py - ИСПРАВЛЕННАЯ ВЕРСИЯ cmd_clarify
@router.message(Command("clarify"))
async def cmd_clarify(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Уточнение к предыдущему вопросу - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # Получаем последний отвеченный вопрос пользователя
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid)
            .where(Question.status == "answered")
            .order_by(Question.answered_at.desc())
            .limit(1)
        )
        last_question = result.scalar_one_or_none()

        if not last_question:
            await message.answer(
                "❌ У вас нет отвеченных вопросов для уточнения.\n\n"
                "Сначала задайте вопрос через /ask и дождитесь ответа."
            )
            return

        # Сохраняем ID вопроса в состоянии
        await state.update_data(clarify_question_id=str(last_question.uuid))
        await state.set_state(UserQAStates.waiting_for_clarification)

        # Показываем оригинальный вопрос и ответ
        # Получаем последний ответ на этот вопрос
        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == last_question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        message_text = f"💬 <b>Уточнение к вопросу:</b>\n\n"
        message_text += f"❓ <b>Ваш вопрос:</b>\n{last_question.text}\n\n"

        if last_answer:
            message_text += f"💬 <b>Полученный ответ:</b>\n{last_answer.text}\n\n"

        message_text += "✍️ <b>Напишите ваше уточнение ниже:</b>\n"
        message_text += "(или /cancel для отмены)"

        await message.answer(message_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in cmd_clarify: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании уточнения.")


@router.message(UserQAStates.waiting_for_clarification)
async def process_clarification(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка уточнения пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("clarify_question_id")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для уточнения.")
            await state.clear()
            return

        # Получаем исходный вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        original_question = result.scalar_one_or_none()

        if not original_question:
            await message.answer("❌ Вопрос не найден.")
            await state.clear()
            return

        # ✅ Добавляем сообщение об уточнении в историю диалога
        await DialogService.add_message(
            db=db,
            question_id=original_question.uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="clarification",
            text=message.text,
        )
        await db.commit()

        # ✅ Получаем полную историю диалога
        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            original_question.uuid, db
        )

        # Показываем пользователю полную историю
        await message.answer(
            f"💬 <b>ВАШЕ УТОЧНЕНИЕ ОТПРАВЛЕНО</b>\n\n"
            f"{history_text}",
            parse_mode="HTML"
        )

        # ✅ Уведомляем фармацевта с полной историей
        # Получаем фармацевта, который взял вопрос
        if original_question.taken_by:
            pharmacist_result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == original_question.taken_by)
            )
            pharmacist = pharmacist_result.scalar_one_or_none()

            if pharmacist and pharmacist.user:
                await message.bot.send_message(
                    chat_id=pharmacist.user.telegram_id,
                    text=f"💬 <b>ПОЛУЧЕНО УТОЧНЕНИЕ</b>\n\n"
                         f"{history_text}",
                    parse_mode="HTML"
                )

        await state.clear()

    except Exception as e:
        logger.error(f"Error processing clarification: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке уточнения.")
        await state.clear()


@router.message(UserQAStates.waiting_for_question)
async def process_user_question(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Упрощенная обработка вопроса от пользователя"""
    logger.info(f"Processing question from user {message.from_user.id}")

    # === ДОБАВИТЬ ПРОВЕРКУ ===
    if not message.text or not message.text.strip():
        await message.answer("❌ Вопрос не может быть пустым. Пожалуйста, напишите текст вопроса.")
        await state.clear()
        return
    # =========================

    if is_pharmacist:
        await message.answer(
            "ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы."
        )
        await state.clear()
        return

    try:
        # Создаем вопрос
        question = Question(
            text=message.text.strip(),
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive(),
        )


        db.add(question)
        await db.commit()
        await db.refresh(question)

        logger.info(
            f"Question created for user {user.telegram_id}, question_id: {question.uuid}"
        )

        # Уведомляем фармацевтов
        try:
            from bot.services.notification_service import (
                notify_pharmacists_about_new_question,
            )

            await DialogService.create_question_message(question, db)
            await notify_pharmacists_about_new_question(question, db)
        except Exception as e:
            logger.error(f"Error in notification service: {e}")

        await message.answer(
            "✅ <b>Ваш вопрос отправлен!</b>\n\n"
            "Фармацевты уже изучают ваш запрос. Вы получите ответ в ближайшее время.\n\n"
            "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
            parse_mode="HTML",
            reply_markup=get_user_keyboard(),
        )

        await state.clear()

    except Exception as e:
        logger.error(
            f"Error processing question from user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer(
            "❌ <b>Не удалось отправить вопрос</b>\n\n"
            "Попробуйте еще раз через несколько минут.",
            parse_mode="HTML",
        )
        await state.clear()


@router.message(UserQAStates.in_dialog)
async def process_dialog_message(
    message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool
):
    """Обработка сообщений в режиме диалога"""
    logger.info(f"Processing dialog message from user {message.from_user.id}")

    if is_pharmacist:
        await message.answer(
            "ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы."
        )
        return

    await message.answer(
        "💬 Сообщение отправлено фармацевту.\n\n"
        "Используйте /done чтобы завершить диалог."
    )


# bot/handlers/user_questions.py - ДОБАВИТЬ НОВЫЙ ОБРАБОТЧИК
@router.callback_query(F.data.startswith("quick_clarify_"))
async def quick_clarify_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Быстрое уточнение через кнопку в сообщении с ответом"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    try:
        question_uuid = callback.data.replace("quick_clarify_", "")

        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Проверяем, что вопрос принадлежит пользователю
        if question.user_id != user.uuid:
            await callback.answer("❌ Этот вопрос не принадлежит вам", show_alert=True)
            return

        # ✅ ОБНОВЛЕНО: Разрешаем уточнение для вопросов с ответами
        # Проверяем, есть ли ответы на этот вопрос
        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        if not last_answer:
            await callback.answer("❌ На этот вопрос еще нет ответа", show_alert=True)
            return

        # Сохраняем ID вопроса в состоянии
        await state.update_data(clarify_question_id=question_uuid)
        await state.set_state(UserQAStates.waiting_for_clarification)

        # Проверяем, запрашивалось ли фото для этого вопроса
        photo_requested = question.context_data and question.context_data.get(
            "photo_requested", False
        )

        message_text = f"💬 <b>Уточнение к вопросу:</b>\n\n"
        message_text += f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"

        if last_answer:
            message_text += f"💬 <b>Полученный ответ:</b>\n{last_answer.text}\n\n"

        if photo_requested:
            message_text += (
                "📸 <b>Фармацевт запросил фото рецепта для этого вопроса.</b>\n"
            )
            message_text += "Вы можете отправить его после уточнения.\n\n"

        message_text += "✍️ <b>Напишите ваше уточнение ниже:</b>\n"
        message_text += "(или /cancel для отмены)"

        await callback.message.answer(message_text, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in quick_clarify_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании уточнения", show_alert=True)


@router.callback_query(F.data.startswith("send_prescription_photo_"))
async def send_prescription_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Обработка нажатия кнопки отправки фото рецепта"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("send_prescription_photo_", "")

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

        # Определяем, какой фармацевт должен получить фото
        pharmacist_id = None

        # 1. Проверяем, есть ли запрос фото в context_data
        if question.context_data and "photo_requested_by" in question.context_data:
            pharmacist_id = question.context_data["photo_requested_by"].get(
                "pharmacist_id"
            )
        # 2. Если нет, проверяем, взят ли вопрос фармацевтом
        elif question.taken_by:
            pharmacist_id = str(question.taken_by)

        if not pharmacist_id:
            await callback.answer(
                "❌ Не найден фармацевт для отправки фото", show_alert=True
            )
            return

        # Получаем фармацевта по ID
        pharmacist_result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        requested_pharmacist = pharmacist_result.scalar_one_or_none()

        if not requested_pharmacist or not requested_pharmacist.user:
            await callback.answer("❌ Фармацевт не найден", show_alert=True)
            return

        # Устанавливаем состояние ожидания фото
        await state.update_data(
            prescription_photo_question_id=question_uuid,
            prescription_photo_pharmacist_id=str(requested_pharmacist.uuid),
            prescription_photo_message_id=callback.message.message_id,
        )
        await state.set_state(UserQAStates.waiting_for_prescription_photo)

        await callback.message.answer(
            "📸 <b>Отправка фото рецепта</b>\n\n"
            "Пожалуйста, отправьте фото рецепта одним из способов:\n\n"
            "1. <b>Как фото</b> - просто прикрепите фото к сообщению\n"
            "2. <b>Как документ</b> - если нужно сохранить качество\n\n"
            f"💡 <b>Фото будет отправлено фармацевту:</b>\n"
            f"👨‍⚕️ {requested_pharmacist.pharmacy_info.get('first_name', '')} "
            f"{requested_pharmacist.pharmacy_info.get('last_name', '')}\n\n"
            "💡 <b>Рекомендации:</b>\n"
            "• Убедитесь, что все надписи читаемы\n"
            "• Хорошее освещение\n"
            "• Весь рецепт в кадре\n\n"
            "Вы можете отправить несколько фото.\n"
            "Когда закончите, нажмите /done\n"
            "Для отмены: /cancel",
            parse_mode="HTML",
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in send_prescription_photo_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(UserQAStates.waiting_for_prescription_photo, F.photo)
async def process_prescription_photo(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка отправленного фото рецепта"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")

        if not question_uuid or not pharmacist_id:
            await message.answer("❌ Не удалось найти вопрос или фармацевта")
            await state.clear()
            return

        # Получаем фармацевта по ID из состояния
        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            await message.answer("❌ Фармацевт не найден")
            await state.clear()
            return

        # Получаем вопрос для информации
        question_result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = question_result.scalar_one_or_none()

        # Формируем ФИО пользователя
        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        # Отправляем фото фармацевту напрямую
        photo = message.photo[-1]  # Берем самую большую версию фото

        # ✅ Добавляем сообщение о фото в историю диалога
        await DialogService.add_message(
            db=db,
            question_id=question_uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="photo",
            file_id=photo.file_id,
            caption=message.caption,
        )
        await db.commit()

        # ✅ Получаем полную историю диалога
        history_text, _ = await DialogService.format_dialog_history_for_display(
            question_uuid, db
        )

        # Отправляем фото с подписью
        await message.bot.send_photo(
            chat_id=pharmacist.user.telegram_id,
            photo=photo.file_id,
            caption=f"📸 <b>Получено фото рецепта</b>\n\n"
                    f"👤 <b>От пользователя:</b> {user_name}\n"
                    f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"{history_text}",
            parse_mode="HTML"
        )

        # Показываем пользователю подтверждение
        await message.answer(
            f"✅ Фото рецепта отправлено фармацевту!\n\n"
            f"📸 <b>Фото добавлено в историю диалога.</b>"
        )

    except Exception as e:
        logger.error(f"Error processing prescription photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке фото")

# Аналогично обновляем process_prescription_document:


@router.message(UserQAStates.waiting_for_prescription_photo, F.document)
async def process_prescription_document(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка отправленного документа (фото рецепта как документ) - БЕЗ СОХРАНЕНИЯ В БД"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")

        if not question_uuid or not pharmacist_id:
            await message.answer("❌ Не удалось найти вопрос или фармацевта")
            await state.clear()
            return

        # Проверяем, что это изображение
        document = message.document
        if not document.mime_type.startswith("image/"):
            await message.answer("❌ Пожалуйста, отправьте изображение (фото)")
            return

        # Получаем фармацевта по ID из состояния
        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == pharmacist_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            await message.answer("❌ Фармацевт не найден")
            await state.clear()
            return

        # Получаем вопрос для информации
        question_result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = question_result.scalar_one_or_none()

        # Формируем ФИО пользователя и фармацевта
        user_name = user.first_name or "Пользователь"
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"

        pharmacist_name = "Фармацевт"
        if pharmacist.pharmacy_info:
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

        # Создаем клавиатуру с кнопками для фармацевта (исправлено)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        pharmacist_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Ответить пользователю",
                        # ИСПРАВЛЕНО: Правильный формат callback_data
                        callback_data=f"answer_{question_uuid}",
                    ),
                    InlineKeyboardButton(
                        text="📸 Запросить еще фото",
                        callback_data=f"request_more_photos_{question_uuid}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Завершить консультацию",
                        callback_data=f"end_dialog_{question_uuid}",
                    )
                ],
            ]
        )

        # Отправляем документ фармацевту напрямую с клавиатурой
        await message.bot.send_document(
            chat_id=pharmacist.user.telegram_id,
            document=document.file_id,
            caption=f"📄 <b>Получен документ с рецептом</b>\n\n"
            f"👤 <b>От пользователя:</b> {user_name}\n"
            f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
            f"❓ <b>По вопросу:</b> {question.text[:100] if question else 'Вопрос не найден'}...\n"
            f"{'💬 <b>Описание:</b> ' + message.caption if message.caption else ''}\n\n"
            f"⚠️ <i>Документ временный и не сохранен в системе</i>\n"
            f"💊 <i>Этот документ был запрошен вами у пользователя</i>",
            parse_mode="HTML",
            reply_markup=pharmacist_keyboard,  # Добавляем клавиатуру
        )

        # ✅ Добавляем сообщение о фото в историю диалога
        await DialogService.add_message(
            db=db,
            question_id=question_uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="photo",
            file_id=document.file_id,
            caption=message.caption,
        )

        await message.answer(
            f"✅ Документ с рецептом отправлен фармацевту {pharmacist_name}!\n\n"
            "Вы можете отправить еще файлы или нажмите /done чтобы завершить."
        )

    except Exception as e:
        logger.error(f"Error processing prescription document: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке документа")


@router.message(Command("done"), UserQAStates.waiting_for_prescription_photo)
async def finish_photo_upload(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Завершение загрузки фото рецепта - БЕЗ БД"""
    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("prescription_photo_question_id")
        pharmacist_id = state_data.get("prescription_photo_pharmacist_id")
        original_message_id = state_data.get("prescription_photo_message_id")

        if pharmacist_id:
            # Получаем фармацевта
            result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == pharmacist_id)
            )
            pharmacist = result.scalar_one_or_none()

            if pharmacist and pharmacist.user:
                # Получаем вопрос для информации
                question = None
                if question_uuid:
                    question_result = await db.execute(
                        select(Question).where(Question.uuid == question_uuid)
                    )
                    question = question_result.scalar_one_or_none()

                # Уведомляем фармацевта о завершении загрузки
                user_name = user.first_name or "Пользователь"
                if user.last_name:
                    user_name = f"{user.first_name} {user.last_name}"

                await message.bot.send_message(
                    chat_id=pharmacist.user.telegram_id,
                    text=f"✅ <b>Пользователь завершил отправку фото рецепта</b>\n\n"
                    f"👤 <b>Пользователь:</b> {user_name}\n"
                    f"❓ <b>Вопрос:</b> {question.text[:150] if question else 'Информация о вопросе недоступна'}...\n\n"
                    f"Все фото рецепта получены и готовы для просмотра.\n"
                    f"💊 <i>Это были фото, которые вы запросили у пользователя</i>",
                    parse_mode="HTML",
                )

        # Редактируем оригинальное сообщение (убираем кнопку)
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=original_message_id,
                reply_markup=None,
            )
        except:
            pass

        await message.answer(
            "✅ Загрузка фото рецепта завершена!\n\n"
            "Фармацевт получил все отправленные вами фото."
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error finishing photo upload: {e}", exc_info=True)
        await message.answer("❌ Ошибка при завершении загрузки")
        await state.clear()
