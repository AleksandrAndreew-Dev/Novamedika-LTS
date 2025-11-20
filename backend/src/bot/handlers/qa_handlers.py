from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.qa_models import User
from db.qa_models import Question
from db.qa_models import Answer
from bot.handlers.qa_states import QAStates
from bot.keyboards.qa_keyboard import make_question_keyboard
import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("online"))
async def set_online(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: User
):
    """Установка статуса онлайн для фармацевта"""
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
        logger.info(
            f"Pharmacist {pharmacist.telegram_id} successfully set online status"
        )

        await message.answer("✅ Вы теперь онлайн и готовы принимать вопросы!")

    except Exception as e:
        logger.error(
            f"Error setting online status for user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при изменении статуса")


@router.message(Command("offline"))
async def set_offline(
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: User
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
            f"Pharmacist {pharmacist.telegram_id} successfully set offline status"
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
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: User
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
    message: Message, db: AsyncSession, is_pharmacist: bool, pharmacist: User
):
    """Показать вопросы с пагинацией"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта команда доступна только фармацевтам")
        return

    try:
        result = await db.execute(
            select(Question)
            .where(Question.status == "pending")
            .order_by(Question.created_at.asc())  # Сначала старые вопросы
            .limit(5)  # Ограничиваем количество
        )
        questions = result.scalars().all()

        if not questions:
            await message.answer(
                "📝 На данный момент нет новых вопросов.\n\n"
                "Пользователи задают вопросы через команду /ask"
            )
            return

        for i, question in enumerate(questions, 1):
            question_text = (
                f"❓ Вопрос #{i}:\n{question.text}\n\n"
                f"🕒 Создан: {question.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

            # Получаем пользователя
            user_result = await db.execute(
                select(User).where(User.uuid == question.user_id)
            )
            user = user_result.scalar_one_or_none()

            if user:
                user_info = user.full_name or user.telegram_username or "Аноним"
                question_text += f"\n👤 Пользователь: {user_info}"

            await message.answer(
                question_text,
                reply_markup=make_question_keyboard(question.uuid)
            )

        if len(questions) == 5:
            await message.answer("💡 Показаны первые 5 вопросов. Ответьте на них чтобы увидеть следующие.")

    except Exception as e:
        logger.error(f"Error in cmd_questions: {e}")
        await message.answer("❌ Ошибка при получении вопросов")


@router.callback_query(F.data.startswith("answer_"))
async def answer_question_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: User,
):
    """Обработка нажатия на кнопку ответа на вопрос"""
    question_uuid = callback.data.replace("answer_", "")

    logger.info(
        f"Answer callback for question {question_uuid} from user {callback.from_user.id}"
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

        # Сохраняем ID вопроса в состоянии
        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        question_preview = (
            question.text[:100] + "..." if len(question.text) > 100 else question.text
        )

        await callback.message.answer(
            f"💬 Вы отвечаете на вопрос:\n\n"
            f"«{question_preview}»\n\n"
            f"Напишите ваш ответ ниже:\n"
            f"(или /cancel для отмены)"
        )

        await callback.answer()

    except Exception as e:
        logger.error(
            f"Error in answer_question_callback for user {callback.from_user.id}: {e}",
            exc_info=True,
        )
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(QAStates.waiting_for_answer)
async def process_answer_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: User,
):
    """Обработка текста ответа на вопрос"""
    logger.info(f"Processing answer from pharmacist {message.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        # Получаем данные из состояния
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        # Создаем ответ
        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )

        db.add(answer)

        # Обновляем статус вопроса
        question.status = "answered"
        question.answered_at = get_utc_now_naive()

        await db.commit()
        logger.info(
            f"Pharmacist {pharmacist.telegram_id} successfully answered question {question.uuid}"
        )

        # Уведомляем пользователя
        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            try:
                answer_preview = (
                    message.text[:100] + "..."
                    if len(message.text) > 100
                    else message.text
                )
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"💊 На ваш вопрос получен ответ от фармацевта:\n\n"
                    f"❓ Ваш вопрос: {question.text}\n\n"
                    f"💬 Ответ: {answer_preview}\n\n"
                    f"Если ответ неполный, задайте уточняющий вопрос через /ask",
                )
                logger.info(
                    f"Notification sent to user {user.telegram_id} about answer"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send notification to user {user.telegram_id}: {e}"
                )

        await message.answer(
            "✅ Ответ успешно отправлен пользователю!\n\n"
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

