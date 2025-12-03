from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.qa_models import User, Question, Answer, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.handlers.common_handlers import get_user_keyboard
from bot.keyboards.qa_keyboard import make_clarification_keyboard

import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()





# В user_questions.py обновляем cmd_ask:
@router.message(Command("ask"))
async def cmd_ask(message: Message):
    """Быстрая команда для вопроса с подсказкой"""
    await message.answer(
        "💬 <b>Просто напишите ваш вопрос в чат!</b>\n\n"
        "Например:\n"
        "• 'Что лучше от температуры?'\n"
        "• 'Можно ли детям принимать ибупрофен?'\n"
        "• 'Какие аналоги у препарата...'\n\n"
        "<i>Пишите прямо здесь ↓</i>",
        parse_mode="HTML"
    )

@router.message(Command("my_questions"))
async def cmd_my_questions(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool
):
    """Показать вопросы пользователя или ответы фармацевта - ОБНОВЛЕННАЯ ВЕРСИЯ С ФИО"""
    logger.info(f"Command /my_questions from user {message.from_user.id}, is_pharmacist: {is_pharmacist}")

    try:
        if is_pharmacist:
            # Для фармацевтов показываем вопросы, на которые они ответили
            logger.info(f"Getting answered questions for pharmacist {user.telegram_id}")

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
            logger.info(f"Getting questions for user {user.telegram_id}")

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
        logger.error(f"Error in cmd_my_questions for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении ваших вопросов. Попробуйте позже.")


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

@router.message(UserQAStates.waiting_for_clarification)
async def process_clarification(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User
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

        # Уведомляем ВСЕХ активных фармацевтов (не только онлайн)
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.is_active == True)  # Все активные фармацевты
        )
        all_active_pharmacists = result.scalars().all()

        notified_count = 0
        for pharmacist in all_active_pharmacists:
            if pharmacist.user and pharmacist.user.telegram_id:
                try:
                    # Разные сообщения для онлайн и офлайн фармацевтов
                    if pharmacist.is_online:
                        message_text = (
                            f"🔔 УТОЧНЕНИЕ К ВОПРОСУ!\n\n"
                            f"❓ Исходный вопрос: {original_question.text}\n\n"
                            f"💬 Уточнение: {message.text}\n\n"
                            f"💡 Статус: Вы в онлайн - можете ответить сразу!"
                        )
                        # Для онлайн фармацевтов отправляем с кнопкой ответа
                        reply_markup = make_clarification_keyboard(clarification_question.uuid)
                    else:
                        message_text = (
                            f"📥 Уточнение к вопросу ожидает ответа\n\n"
                            f"❓ Исходный вопрос: {original_question.text}\n\n"
                            f"💬 Уточнение: {message.text}\n\n"
                            f"💡 Статус: Вы в офлайн - перейдите в онлайн чтобы ответить\n"
                            f"Используйте /online чтобы начать принимать вопросы"
                        )
                        reply_markup = None

                    await message.bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text,
                        reply_markup=reply_markup
                    )
                    notified_count += 1
                    logger.info(f"Clarification notification sent to pharmacist {pharmacist.user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to notify pharmacist {pharmacist.user.telegram_id}: {e}")

        logger.info(f"Notified {notified_count} pharmacists about clarification for question {original_question.uuid}")

        await message.answer(
            "✅ Ваше уточнение отправлено фармацевтам!\n\n"
            f"👨‍⚕️ Уведомлено фармацевтов: {notified_count}\n\n"
            "Фармацевт скоро ответит на ваше уточнение."
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
            "Используйте «Мои вопросы» чтобы отслеживать статус.",
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
