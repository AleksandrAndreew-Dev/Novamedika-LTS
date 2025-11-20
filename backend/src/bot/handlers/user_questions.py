from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.qa_models import User
from db.qa_models import Question
from db.qa_models import Answer
from db.qa_models import Pharmacist
from bot.handlers.qa_states import UserQAStates
import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()



@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext, db: AsyncSession, is_pharmacist: bool):
    """Начало процесса задания вопроса"""
    logger.info(f"Command /ask from user {message.from_user.id}, is_pharmacist: {is_pharmacist}")

    if is_pharmacist:
        await message.answer("ℹ️ Вы фармацевт. Используйте /questions для ответов на вопросы.")
        return

    await state.set_state(UserQAStates.waiting_for_question)
    await message.answer(
        "💬 Напишите ваш вопрос фармацевту:\n\n"
        "Опишите подробно вашу проблему или вопрос, и фармацевт скоро ответит.\n"
        "(или /cancel для отмены)"
    )

@router.message(Command("my_questions"))
async def cmd_my_questions(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool
):
    """Показать вопросы пользователя или ответы фармацевта"""
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

                        pharmacist_name = "Фармацевт"
                        if pharmacist and pharmacist.pharmacy_info:
                            pharmacy_name = pharmacist.pharmacy_info.get('name', 'Фармацевт')
                            pharmacist_name = pharmacy_name

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

@router.message(UserQAStates.waiting_for_question)
async def process_user_question(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    user: User
):
    """Обработка вопроса от пользователя"""
    logger.info(f"Processing question from user {message.from_user.id}, state: {await state.get_state()}")

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
        logger.info(f"Question created for user {user.telegram_id}, question_id: {question.uuid}")

        # Ищем онлайн фармацевтов с подгрузкой пользователя
        five_minutes_ago = get_utc_now_naive() - timedelta(minutes=5)

        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))  # Подгружаем связанного пользователя
            .where(
                and_(
                    Pharmacist.is_online == True,
                    Pharmacist.last_seen >= five_minutes_ago
                )
            )
        )
        online_pharmacists = result.scalars().all()

        logger.info(f"Found {len(online_pharmacists)} online pharmacists")

        # Уведомляем онлайн фармацевтов
        notified_count = 0
        for pharmacist in online_pharmacists:
            try:
                # ИСПРАВЛЕНИЕ: используем pharmacist.user.telegram_id
                if pharmacist.user and pharmacist.user.telegram_id:
                    question_preview = message.text[:100] + "..." if len(message.text) > 100 else message.text
                    await message.bot.send_message(
                        chat_id=pharmacist.user.telegram_id,  # ИСПРАВЛЕНО
                        text=f"🔔 Новый вопрос от пользователя!\n\n"
                             f"❓ Вопрос: {question_preview}\n\n"
                             f"Используйте /questions чтобы ответить"
                    )
                    notified_count += 1
                    logger.info(f"Notification sent to pharmacist {pharmacist.user.telegram_id}")  # ИСПРАВЛЕНО
            except Exception as e:
                # ИСПРАВЛЕНИЕ: в логировании тоже исправляем
                pharmacist_id = pharmacist.user.telegram_id if pharmacist.user else "unknown"
                logger.error(f"Failed to notify pharmacist {pharmacist_id}: {e}")

        await message.answer(
            "✅ Ваш вопрос отправлен фармацевтам!\n\n"
            f"📊 Статус: Ожидание ответа\n"
            f"👨‍⚕️ Уведомлено фармацевтов: {notified_count}\n\n"
            "Вы получите уведомление, когда фармацевт ответит на ваш вопрос.\n"
            "Используйте /my_questions чтобы посмотреть статус ваших вопросов."
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error processing question from user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке вопроса. Попробуйте позже.")
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
