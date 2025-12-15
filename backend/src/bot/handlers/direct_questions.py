from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select  # ДОБАВИТЬ
import logging

from db.qa_models import User, Question
from utils.time_utils import get_utc_now_naive
from bot.services.notification_service import notify_pharmacists_about_new_question
from bot.handlers.qa_states import UserQAStates
from bot.services.dialog_service import DialogService
from bot.handlers.user_questions import process_dialog_message  
from bot.keyboards.qa_keyboard import make_completed_dialog_keyboard

logger = logging.getLogger(__name__)
router = Router()


def should_create_question(text: str) -> bool:
    """Определяет, стоит ли создавать вопрос из текста"""
    text_lower = text.lower().strip()

    # 0. Проверяем, является ли это командой (начинается с /)
    if text.startswith("/"):
        return False

    # 2. Проверяем длину (минимально 2 символов)
    if len(text_lower) < 2:
        return False

    # 3. Проверяем, что это не просто набор символов или цифр
    if (
        text_lower.replace("?", "")
        .replace("!", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
        .isdigit()
    ):
        return False

    # 4. Проверяем на явные команды (даже без /)
    if text_lower.startswith(("список", "помощь", "команды", "меню", "старт")):
        return False

    return True


@router.message(F.text & ~F.command)
async def handle_direct_text(
    message: Message,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Обработка прямых текстовых сообщений как вопросов С ПРОВЕРКАМИ"""

    if is_pharmacist:
        return

    current_state = await state.get_state()

    # Проверяем, есть ли активные диалоги у пользователя
    if current_state is None:
        # Проверяем есть ли активные вопросы (in_progress или answered)
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
        active_question = result.scalar_one_or_none()

        if active_question:
            # ✅ ПРОВЕРКА: Не завершен ли диалог
            if active_question.status == "completed":
                await message.answer(
                    "🎯 <b>Ваша предыдущая консультация завершена</b>\n\n"
                    f"❓ Вопрос: {active_question.text[:200]}...\n\n"
                    "Чтобы задать новый вопрос, просто напишите его в чат.\n"
                    "Или используйте кнопки ниже:",
                    parse_mode="HTML",
                    reply_markup=make_completed_dialog_keyboard(active_question.uuid)
                )
                return

            # Автоматически продолжаем диалог
            await state.update_data(active_dialog_question_id=str(active_question.uuid))
            await state.set_state(UserQAStates.in_dialog)

            # Пересылаем сообщение как продолжение диалога
            await process_dialog_message(message, state, db, user, is_pharmacist)
            return

    # ... остальной код без изменений

    # Остальной код оставить без изменений...
    if current_state is not None:
        # Для этих состояний пропускаем обработку (уже есть другие обработчики)
        if current_state in [
            UserQAStates.waiting_for_prescription_photo,
            UserQAStates.waiting_for_clarification,
            UserQAStates.in_dialog,
            UserQAStates.waiting_for_question,
        ]:
            return

        # Для других состояний сбрасываем
        await state.clear()

    # Проверяем текст
    if not message.text or not message.text.strip():
        return

    if not should_create_question(message.text):
        return

    try:
        # Создаем вопрос
        question = Question(
            text=message.text,
            user_id=user.uuid,
            status="pending",
            created_at=get_utc_now_naive(),
        )

        db.add(question)
        await db.commit()
        await db.refresh(question)

        # ✅ ЛОГИРОВАНИЕ: Отслеживаем создание вопроса
        logger.info(
            f"Direct question created: ID={question.uuid}, text='{message.text[:50]}...'"
        )

        # СОЗДАЕМ ПЕРВОЕ СООБЩЕНИЕ В ИСТОРИИ ДИАЛОГА
        dialog_message = await DialogService.create_question_message(question, db)
        await db.commit()  # Фиксируем создание сообщения

        # ✅ ЛОГИРОВАНИЕ: Отслеживаем создание сообщения в диалоге
        logger.info(
            f"Dialog message created: question_id={dialog_message.question_id}, type={dialog_message.message_type}"
        )

        # Проверяем, есть ли сообщения в истории
        history = await DialogService.get_dialog_history(question.uuid, db, limit=10)
        logger.info(f"Dialog history after creation: {len(history)} messages")

        # Уведомляем фармацевтов
        await notify_pharmacists_about_new_question(question, db)

        # Подтверждение пользователю
        await message.answer(
            "✅ <b>Вопрос отправлен!</b>\n\n"
            "Фармацевты получили уведомление и скоро ответят.\n\n"
            "💡 <i>Используйте /my_questions чтобы отслеживать статус</i>",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in direct question: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при отправке вопроса. Пожалуйста, попробуйте еще раз.",
            parse_mode="HTML",
        )
