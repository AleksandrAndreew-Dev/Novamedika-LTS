from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from db.qa_models import User, Question, Answer
from bot.services.dialog_service import DialogService
from bot.handlers.qa_states import UserQAStates
from bot.services.notification_service import notify_about_clarification

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("clarify"))
@router.callback_query(F.data == "clarify_question")
async def clarify_command_handler(
    update: Message | CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User
):
    """Обработчик команды уточнения - показываем вопросы для уточнения"""
    try:
        # Получаем отвеченные вопросы пользователя
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid)
            .where(Question.status == "answered")
            .order_by(Question.answered_at.desc())
            .limit(10)
        )
        answered_questions = result.scalars().all()

        if not answered_questions:
            message = "❌ У вас нет отвеченных вопросов для уточнения."
            if isinstance(update, CallbackQuery):
                await update.message.answer(message)
                await update.answer()
            else:
                await update.answer(message)
            return

        # Создаем клавиатуру с вопросами для уточнения
        keyboard_buttons = []
        for question in answered_questions:
            question_preview = question.text[:50] + "..." if len(question.text) > 50 else question.text
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"❓ {question_preview}",
                    callback_data=f"clarify_select_{question.uuid}"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        message_text = (
            "✍️ <b>Выберите вопрос для уточнения:</b>\n\n"
            "Нажмите на вопрос ниже, чтобы добавить уточнение."
        )

        if isinstance(update, CallbackQuery):
            await update.message.answer(message_text, parse_mode="HTML", reply_markup=keyboard)
            await update.answer()
        else:
            await update.answer(message_text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in clarify_command_handler: {e}", exc_info=True)
        error_msg = "❌ Ошибка при получении списка вопросов."
        if isinstance(update, CallbackQuery):
            await update.message.answer(error_msg)
            await update.answer()
        else:
            await update.answer(error_msg)


def is_not_command(text: str | None) -> bool:
    """Проверка, что текст не является командой"""
    if text is None:
        return False
    return not text.startswith('/')


@router.message(UserQAStates.waiting_for_clarification & F.text)
async def process_clarification(
    message: Message, state: FSMContext, db: AsyncSession, user: User
):
    """Обработка уточнения пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    # Игнорируем команды в состоянии ожидания уточнения
    if not is_not_command(message.text):
        return
    
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

        # Проверяем, что вопрос имеет статус "answered"
        if original_question.status != "answered":
            await message.answer("❌ На этот вопрос еще нет ответа.")
            await state.clear()
            return

        # ✅ Добавляем сообщение об уточнении в диалог
        await DialogService.add_message(
            db=db,
            question_id=original_question.uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="clarification",
            text=message.text,
        )
        await db.commit()

        # ✅ Уведомляем о новом уточнении
        await notify_about_clarification(
            original_question=original_question,
            clarification_text=message.text,
            db=db
        )

        # ✅ ОТПРАВЛЯЕМ ПОЛЬЗОВАТЕЛЮ ИСТОРИЮ С УТОЧНЕНИЕМ
        await DialogService.send_unified_dialog_history(
            bot=message.bot,
            chat_id=message.chat.id,
            question_uuid=original_question.uuid,
            db=db,
            title="ВАШЕ УТОЧНЕНИЕ ОТПРАВЛЕНО",
            pre_text="💬 <b>ВАШЕ УТОЧНЕНИЕ ОТПРАВЛЕНО</b>\n\n",
            post_text=None,
            is_pharmacist=False,
            show_buttons=True
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error processing clarification: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке уточнения.")
        await state.clear()


@router.callback_query(F.data.startswith("clarify_select_"))
async def clarify_select_question(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User
):
    """Выбор конкретного вопроса для уточнения"""
    question_uuid = callback.data.replace("clarify_select_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
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
        await state.update_data(clarify_question_id=str(question.uuid))
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
        logger.error(f"Error in clarify_select_question: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при выборе вопроса", show_alert=True)
