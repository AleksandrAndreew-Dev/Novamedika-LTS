from aiogram.types import Message as AiogramMessage
from typing import Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload  # Добавьте эту строку

from db.qa_models import User, Question, Answer, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers import get_user_keyboard

from bot.services.notification_service import notify_about_clarification

import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()





@router.message(Command("ask"))
async def cmd_ask(message: Message):
    """Быстрая команда для вопроса"""
    await message.answer(
        "📝 <b>Просто напишите ваш вопрос в чат!</b>\n\n"
        "Не нужно нажимать кнопки или писать команды — просто опишите вашу проблему.\n\n"
        "<i>Пишите прямо здесь ↓</i>",
        parse_mode="HTML"
    )

@router.message(Command("my_questions"))
@router.callback_query(F.data == "my_questions_callback")
async def cmd_my_questions(
    update: Union[Message, CallbackQuery],
    db: AsyncSession,
    user: User,
    is_pharmacist: bool
):
    """Показать вопросы пользователя или ответы фармацевта - ИСПРАВЛЕННАЯ ВЕРСИЯ"""

    # Обрабатываем разные типы входящих данных
    if isinstance(update, CallbackQuery):
        message = update.message
        from_user = update.from_user
        is_callback = True
    else:
        message = update
        from_user = update.from_user
        is_callback = False

    logger.info(f"Command /my_questions from user {from_user.id}, is_pharmacist: {is_pharmacist}")

    try:
        if is_pharmacist:
            # Для фармацевтов показываем вопросы, на которые они ответили
            logger.info(f"Getting answered questions for pharmacist {from_user.id}")

            result = await db.execute(
                select(Question)
                .join(Answer, Answer.question_id == Question.uuid)
                .where(Answer.pharmacist_id == user.uuid)
                .order_by(Answer.created_at.desc())
                .limit(20)
            )
            answered_questions = result.scalars().all()

            logger.info(f"Found {len(answered_questions)} answered questions for pharmacist {user.telegram_id}")

            if not answered_questions:
                await message.answer("📝 Вы еще не ответили ни на один вопрос.")
                return

            questions_text = "📋 Ваши ответы на вопросы:\n\n"

            for i, question in enumerate(answered_questions, 1):
                # Получаем последний ответ этого фармацевта на данный вопрос
                answer_result = await db.execute(
                    select(Answer)
                    .where(
                        and_(
                            Answer.question_id == question.uuid,
                            Answer.pharmacist_id == user.uuid
                        )
                    )
                    .order_by(Answer.created_at.desc())
                    .limit(1)
                )
                answer = answer_result.scalar_one_or_none()

                questions_text += f"{i}. ❓ Вопрос: {question.text[:100]}{'...' if len(question.text) > 100 else ''}\n"
                if answer:
                    answer_preview = answer.text[:100] + "..." if len(answer.text) > 100 else answer.text
                    questions_text += f"   💬 Ваш ответ: {answer_preview}\n"
                questions_text += f"   🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                questions_text += "   ---\n\n"

            await message.answer(questions_text)

        else:
            # Для обычных пользователей показываем их вопросы
            logger.info(f"Getting questions for user {from_user.id}")

            result = await db.execute(
                select(Question)
                .where(Question.user_id == user.uuid)
                .order_by(Question.created_at.desc())
                .limit(20)
            )
            user_questions = result.scalars().all()

            logger.info(f"Found {len(user_questions)} questions for user {user.telegram_id}")

            if not user_questions:
                await message.answer("📝 У вас пока нет вопросов.\n\nИспользуйте /ask чтобы задать первый вопрос!")
                return

            questions_text = "📋 Ваши вопросы:\n\n"

            for i, question in enumerate(user_questions, 1):
                questions_text += f"{i}. ❓ Вопрос: {question.text}\n"
                questions_text += f"   📊 Статус: {question.status}\n"

                # ИСПРАВЛЕНИЕ: избегаем ленивой загрузки answers
                # Вместо question.answers делаем отдельный запрос
                answers_result = await db.execute(
                    select(Answer)
                    .where(Answer.question_id == question.uuid)
                    .order_by(Answer.created_at.asc())
                )
                answers = answers_result.scalars().all()

                if question.status == "answered":
                    # Создаем кнопку уточнения для каждого отвеченного вопроса
                    clarify_keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✍️ Уточнить этот вопрос",
                                    callback_data=f"quick_clarify_{question.uuid}"
                                )
                            ]
                        ]
                    )

                    # Отправляем отдельное сообщение с кнопкой для каждого отвеченного вопроса
                    await message.answer(
                        f"❓ Вопрос: {question.text[:200]}...\n"
                        f"✅ Отвечен: {question.answered_at.strftime('%d.%m.%Y %H:%M')}",
                        reply_markup=clarify_keyboard
                    )

                if answers:
                    questions_text += "   💬 Ответы:\n"
                    for answer in answers:
                        # Получаем информацию о фармацевте
                        pharmacist_result = await db.execute(
                            select(Pharmacist).where(Pharmacist.uuid == answer.pharmacist_id)
                        )
                        pharmacist = pharmacist_result.scalar_one_or_none()

                        # Формируем имя фармацевта с ФИО
                        pharmacist_name = "Фармацевт"
                        if pharmacist and pharmacist.pharmacy_info:
                            first_name = pharmacist.pharmacy_info.get('first_name', '')
                            last_name = pharmacist.pharmacy_info.get('last_name', '')
                            patronymic = pharmacist.pharmacy_info.get('patronymic', '')

                            name_parts = []
                            if last_name:
                                name_parts.append(last_name)
                            if first_name:
                                name_parts.append(first_name)
                            if patronymic:
                                name_parts.append(patronymic)

                            pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"

                        answer_preview = answer.text[:80] + "..." if len(answer.text) > 80 else answer.text
                        questions_text += f"     - {pharmacist_name}: {answer_preview}\n"

                questions_text += f"   🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"

                if question.answered_at:
                    questions_text += f"   ✅ Ответ получен: {question.answered_at.strftime('%d.%m.%Y %H:%M')}\n"

                questions_text += "   ---\n\n"

            await message.answer(questions_text)


    except Exception as e:
        logger.error(f"Error in cmd_my_questions for user {from_user.id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении ваших вопросов. Попробуйте позже.")
    if is_callback:
        await update.answer()

@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Завершение диалога"""
    logger.info(f"Command /done from user {message.from_user.id}, is_pharmacist: {is_pharmacist}")

    current_state = await state.get_state()

    if current_state == UserQAStates.in_dialog:
        await state.clear()
        await message.answer(
            "✅ Диалог завершен.\n\n"
            "Если у вас есть еще вопросы, используйте /ask"
        )
    else:
        await message.answer("ℹ️ В данный момент у вас нет активного диалога.")


# bot/handlers/user_questions.py - ИСПРАВЛЕННАЯ ВЕРСИЯ cmd_clarify
@router.message(Command("clarify"))
async def cmd_clarify(message: Message, state: FSMContext, db: AsyncSession, user: User):
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

# bot/handlers/user_questions.py - обновляем process_clarification
@router.message(UserQAStates.waiting_for_clarification)
async def process_clarification(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User
):
    """Обработка уточнения пользователя"""
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

        # Создаем новый вопрос как уточнение
        clarification_question = Question(
            text=f"Уточнение: {message.text}",
            user_id=user.uuid,
            status="pending",
            category=original_question.category,
            context_data={
                "is_clarification": True,
                "original_question_id": str(original_question.uuid),
                "original_question_text": original_question.text
            }
        )

        db.add(clarification_question)
        await db.commit()
        await db.refresh(clarification_question)

        # Уведомляем о новом уточнении
        await notify_about_clarification(
            clarification_question,
            original_question,
            db
        )

        await message.answer(
            "✅ Ваше уточнение отправлено!\n\n"
            "Фармацевт, который взял ваш вопрос, получил уведомление и скоро ответит."
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error processing clarification: {e}")
        await message.answer("❌ Ошибка при отправке уточнения.")
        await state.clear()

@router.message(UserQAStates.waiting_for_question)
async def process_user_question(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    user: User
):
    """Упрощенная обработка вопроса от пользователя"""
    logger.info(f"Processing question from user {message.from_user.id}")

    if is_pharmacist:
        await message.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.")
        await state.clear()
        return

    try:
        # Создаем вопрос
        question = Question(
            text=message.text,
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive()
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)
        logger.info(f"Question created for user {user.telegram_id}, question_id: {question.uuid}")

        # Уведомляем фармацевтов
        try:
            from bot.services.notification_service import notify_pharmacists_about_new_question
            await notify_pharmacists_about_new_question(question, db)
        except Exception as e:
            logger.error(f"Error in notification service: {e}")

        await message.answer(
        "✅ <b>Ваш вопрос отправлен!</b>\n\n"
        "Фармацевты уже изучают ваш запрос. Вы получите ответ в ближайшее время.\n\n"
        "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
        parse_mode="HTML",
        reply_markup=get_user_keyboard()
    )

        await state.clear()

    except Exception as e:
        logger.error(f"Error processing question from user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Не удалось отправить вопрос</b>\n\n"
            "Попробуйте еще раз через несколько минут.",
            parse_mode="HTML"
        )
        await state.clear()

@router.message(UserQAStates.in_dialog)
async def process_dialog_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool
):
    """Обработка сообщений в режиме диалога"""
    logger.info(f"Processing dialog message from user {message.from_user.id}")

    if is_pharmacist:
        await message.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.")
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
    is_pharmacist: bool
):
    """Быстрое уточнение через кнопку в сообщении с ответом"""
    if is_pharmacist:
        await callback.answer("❌ Эта функция доступна только пользователям", show_alert=True)
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

        # Проверяем, что вопрос отвечен
        if question.status != "answered":
            await callback.answer("❌ Этот вопрос еще не получил ответ", show_alert=True)
            return

        # Получаем последний ответ на вопрос
        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        # Сохраняем ID вопроса в состоянии
        await state.update_data(clarify_question_id=question_uuid)
        await state.set_state(UserQAStates.waiting_for_clarification)

        message_text = f"💬 <b>Уточнение к вопросу:</b>\n\n"
        message_text += f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"

        if last_answer:
            message_text += f"💬 <b>Полученный ответ:</b>\n{last_answer.text}\n\n"

        message_text += "✍️ <b>Напишите ваше уточнение ниже:</b>\n"
        message_text += "(или /cancel для отмены)"

        await callback.message.answer(message_text, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in quick_clarify_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании уточнения", show_alert=True)

# В файл user_questions.py добавить

# В user_questions.py, обновляем функцию send_prescription_photo_callback:

@router.callback_query(F.data.startswith("send_prescription_photo_"))
async def send_prescription_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool
):
    """Обработка нажатия кнопки отправки фото рецепта"""
    if is_pharmacist:
        await callback.answer("❌ Эта функция доступна только пользователям", show_alert=True)
        return

    question_uuid = callback.data.replace("send_prescription_photo_", "")

    try:
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден или не принадлежит вам", show_alert=True)
            return

        # ВАЖНО: Получаем информацию о фармацевте, который запросил фото
        photo_requested_by = None
        if question.context_data and "photo_requested_by" in question.context_data:
            photo_requested_by = question.context_data["photo_requested_by"]
            pharmacist_id = photo_requested_by.get("pharmacist_id")

            # Получаем фармацевта по ID
            pharmacist_result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == pharmacist_id)
            )
            requested_pharmacist = pharmacist_result.scalar_one_or_none()
        else:
            # Если нет информации о запросе, берем фармацевта, который взял вопрос
            pharmacist_result = await db.execute(
                select(Question)
                .options(
                    selectinload(Question.taken_pharmacist).selectinload(Pharmacist.user)
                )
                .where(Question.uuid == question_uuid)
            )
            question_with_pharm = pharmacist_result.scalar_one_or_none()
            requested_pharmacist = question_with_pharm.taken_pharmacist if question_with_pharm else None

        if not requested_pharmacist or not requested_pharmacist.user:
            await callback.answer("❌ Фармацевт, запросивший фото, не найден", show_alert=True)
            return

        # Устанавливаем состояние ожидания фото
        await state.update_data(
            prescription_photo_question_id=question_uuid,
            prescription_photo_pharmacist_id=str(requested_pharmacist.uuid),
            prescription_photo_message_id=callback.message.message_id
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
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in send_prescription_photo_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)

# В user_questions.py, обновляем process_prescription_photo:

@router.message(UserQAStates.waiting_for_prescription_photo, F.photo)
async def process_prescription_photo(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User
):
    """Обработка отправленного фото рецепта - БЕЗ СОХРАНЕНИЯ В БД"""
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

        # Формируем ФИО фармацевта
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

        # Отправляем фото фармацевту напрямую (без сохранения в БД)
        photo = message.photo[-1]  # Берем самую большую версию фото

        await message.bot.send_photo(
            chat_id=pharmacist.user.telegram_id,
            photo=photo.file_id,
            caption=f"📸 <b>Получено фото рецепта</b>\n\n"
                   f"👤 <b>От пользователя:</b> {user_name}\n"
                   f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
                   f"❓ <b>По вопросу:</b> {question.text[:100] if question else 'Вопрос не найден'}...\n"
                   f"{'💬 <b>Описание:</b> ' + message.caption if message.caption else ''}\n\n"
                   f"⚠️ <i>Фото временное и не сохранено в системе</i>\n"
                   f"💊 <i>Это фото было запрошено вами у пользователя</i>",
            parse_mode="HTML"
        )

        await message.answer(
            f"✅ Фото рецепта отправлено фармацевту {pharmacist_name}!\n\n"
            "Вы можете отправить еще фото или нажмите /done чтобы завершить."
        )

    except Exception as e:
        logger.error(f"Error processing prescription photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке фото")

# Аналогично обновляем process_prescription_document:

@router.message(UserQAStates.waiting_for_prescription_photo, F.document)
async def process_prescription_document(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User
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
        if not document.mime_type.startswith('image/'):
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

        # Формируем ФИО пользователя и фармацевта (как в process_prescription_photo)
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

        # Отправляем документ фармацевту напрямую
        await message.bot.send_document(
            chat_id=pharmacist.user.telegram_id,
            document=document.file_id,
            caption=f"📄 <b>Получен документ с рецептом</b>\n\n"
                   f"👤 <b>От пользователя:</b> {user_name}\n"
                   f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
                   f"❓ <b>По вопросу:</b> {question.text[:100] if question else 'Вопрос не найден'}...\n"
                   f"{'💬 <b>Описание:</b> ' + message.caption if message.caption else ''}\n\n"
                   f"⚠️ <i>Документ временный и не сохранен в системе</i>\n"
                   f"💊 <i>Это документ был запрошен вами у пользователя</i>",
            parse_mode="HTML"
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
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User
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
                    parse_mode="HTML"
                )

        # Редактируем оригинальное сообщение (убираем кнопку)
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=original_message_id,
                reply_markup=None
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
