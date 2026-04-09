"""Callback-обработчики диалогов: история, просмотр, освобождение, ответ."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from utils.time_utils import get_utc_now_naive
from db.qa_models import User, Pharmacist, Question, Answer
from bot.handlers.qa_states import QAStates
from bot.keyboards.qa_keyboard import make_pharmacist_dialog_keyboard
from bot.services.dialog_service import DialogService
from bot.services.assignment_service import QuestionAssignmentService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("show_history_"))
async def show_dialog_history_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
):
    """Показать полную историю диалога"""
    question_uuid = callback.data.replace("show_history_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if is_pharmacist:
            if question.taken_by != pharmacist.uuid and question.taken_by is not None:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return
        else:
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question_uuid, db
        )

        await callback.message.answer(history_text, parse_mode="HTML")

        if file_ids:
            for file_id in file_ids:
                try:
                    await callback.message.answer_photo(
                        file_id, caption="📸 Фото из истории диалога"
                    )
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")
                    await callback.message.answer(
                        "⚠️ Не удалось отправить одно из фото (файл устарел)"
                    )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_dialog_history_callback: {e}")
        await callback.answer("❌ Ошибка при загрузке истории", show_alert=True)


@router.callback_query(F.data.startswith("view_dialog_"))
async def view_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
):
    """Просмотр диалога с историей"""
    question_uuid = callback.data.replace("view_dialog_", "")

    try:
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if is_pharmacist:
            if question.taken_by != pharmacist.uuid and question.taken_by is not None:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return
        else:
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

        messages = await DialogService.get_dialog_history(question.uuid, db, limit=5)

        if is_pharmacist:
            user_info = f"{question.user.first_name or 'Пользователь'}"
            if question.user.last_name:
                user_info = f"{question.user.first_name} {question.user.last_name}"
            message_text = (
                f"💬 <b>ДИАЛОГ С ПОЛЬЗОВАТЕЛЕМ</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_info}\n"
                f"❓ <b>Вопрос:</b> {question.text[:200]}...\n\n"
            )
        else:
            message_text = (
                f"💬 <b>ВАШ ДИАЛОГ С ФАРМАЦЕВТОМ</b>\n\n"
                f"❓ <b>Ваш вопрос:</b> {question.text[:200]}...\n\n"
            )

        if messages:
            message_text += "<b>Последние сообщения:</b>\n"
            message_text += "─" * 20 + "\n"

            for msg in reversed(messages[-3:]):
                if msg.sender_type == "user":
                    sender = "👤 Вы" if not is_pharmacist else "👤 Пользователь"
                else:
                    sender = "👨‍⚕️ Фармацевт"

                time_str = msg.created_at.strftime("%H:%M")

                if msg.message_type == "question":
                    preview = (
                        f"❓ {msg.text[:80]}..."
                        if len(msg.text) > 80
                        else f"❓ {msg.text}"
                    )
                elif msg.message_type == "answer":
                    preview = (
                        f"💬 {msg.text[:80]}..."
                        if len(msg.text) > 80
                        else f"💬 {msg.text}"
                    )
                elif msg.message_type == "clarification":
                    preview = (
                        f"🔍 {msg.text[:80]}..."
                        if len(msg.text) > 80
                        else f"🔍 {msg.text}"
                    )
                elif msg.message_type == "photo":
                    preview = "📸 Фото рецепта"
                else:
                    preview = (
                        f"💭 {msg.text[:80]}..."
                        if len(msg.text) > 80
                        else f"💭 {msg.text}"
                    )

                message_text += f"{sender} [{time_str}]: {preview}\n"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Полная история диалога",
                        callback_data=f"show_history_{question.uuid}",
                    )
                ],
                [
                    (
                        InlineKeyboardButton(
                            text="💬 Продолжить общение",
                            callback_data=f"answer_{question.uuid}",
                        )
                        if is_pharmacist
                        else InlineKeyboardButton(
                            text="✍️ Уточнить",
                            callback_data=f"quick_clarify_{question.uuid}",
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Завершить диалог",
                        callback_data=f"end_dialog_{question.uuid}",
                    )
                ],
            ]
        )

        await callback.message.answer(
            message_text, parse_mode="HTML", reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при просмотре диалога", show_alert=True)


@router.callback_query(F.data.startswith("view_only_"))
async def view_only_question_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Просмотр вопроса, который уже взят другим фармацевтом"""
    question_uuid = callback.data.replace("view_only_", "")

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

        pharmacist_info = ""
        if question.taken_by:
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

                pharmacist_name = " ".join(name_parts) if name_parts else "Фармацевт"
                chain = taken_pharmacist.pharmacy_info.get("chain", "")
                number = taken_pharmacist.pharmacy_info.get("number", "")

                pharmacist_info = f"👨‍⚕️ <b>Взял:</b> {pharmacist_name}"
                if chain and number:
                    pharmacist_info += f" ({chain}, аптека №{number})"
                if question.taken_at:
                    pharmacist_info += f"\n⏰ <b>Время взятия:</b> {question.taken_at.strftime('%H:%M:%S')}"

        message_text = (
            f"🔴 <b>ВОПРОС УЖЕ ВЗЯТ ДРУГИМ ФАРМАЦЕВТОМ</b>\n\n"
            f"{pharmacist_info}\n\n"
            f"❓ <b>Вопрос:</b>\n{question.text}\n\n"
            f"🕒 <b>Создан:</b> {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 <b>Статус:</b> В работе другим фармацевтом"
        )

        await callback.message.answer(message_text, parse_mode="HTML")
        await callback.answer("Этот вопрос уже взят другим фармацевтом")

    except Exception as e:
        logger.error(f"Error in view_only_question_callback: {e}")
        await callback.answer("❌ Ошибка при просмотре вопроса", show_alert=True)


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


@router.callback_query(F.data.startswith("answer_"))
async def answer_question_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка нажатия на кнопку ответа на вопрос С ПРОВЕРКОЙ ЗАВЕРШЕНИЯ"""
    question_uuid = callback.data.replace("answer_", "")

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

        if question.status == "completed":
            await callback.answer("✅ Этот диалог уже завершен", show_alert=True)
            await callback.message.answer(
                f"🎯 <b>ЗАВЕРШЕННЫЙ ДИАЛОГ</b>\n\n"
                f"❓ Вопрос: {question.text[:200]}...\n\n"
                f"⏰ Завершен: {question.answered_at.strftime('%d.%m.%Y %H:%M') if question.answered_at else 'Дата не указана'}\n\n"
                "<i>Этот диалог был завершен и больше не доступен для общения.</i>",
                parse_mode="HTML",
            )
            return

        if question.status == "pending" or question.taken_by != pharmacist.uuid:
            assignment_success = (
                await QuestionAssignmentService.assign_question_to_pharmacist(
                    question_uuid, str(pharmacist.uuid), db
                )
            )
            await state.update_data(
                question_uuid=question_uuid, dialog_partner_id=str(pharmacist.uuid)
            )
            await state.set_state(QAStates.in_dialog_with_user)

            if not assignment_success:
                await callback.answer(
                    "❌ Ошибка при назначении вопроса", show_alert=True
                )
                return

            question.taken_by = pharmacist.uuid
            question.taken_at = get_utc_now_naive()
            question.status = "in_progress"
            await db.commit()

        await state.update_data(question_uuid=question_uuid)
        await state.set_state(QAStates.waiting_for_answer)

        question_preview = (
            question.text[:300] + "..." if len(question.text) > 300 else question.text
        )

        await callback.message.answer(
            f"💬 <b>Вы в диалоге с пользователем</b>\n\n"
            f"❓ Вопрос: {question_preview}\n\n"
            f"Напишите ваш ответ или уточняющий вопрос:\n"
            f"(или нажмите кнопки ниже для других действий)",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in answer_question_callback: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


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
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        answer_result = await db.execute(
            select(Answer)
            .where(Answer.question_id == question.uuid)
            .order_by(Answer.created_at.desc())
            .limit(1)
        )
        last_answer = answer_result.scalar_one_or_none()

        if not last_answer and question.status != "answered":
            await callback.answer("❌ На этот вопрос еще нет ответа", show_alert=True)
            return

        await state.update_data(
            question_uuid=question_uuid,
            is_clarification=True,
        )
        await state.set_state(QAStates.waiting_for_answer)

        await callback.message.answer(
            f"🔍 Вы отвечаете на <b>УТОЧНЕНИЕ</b>:\n\n"
            f"❓ <b>Вопрос:</b>\n{question.text}\n\n"
            f"💬 <b>Предыдущий ответ:</b>\n{last_answer.text if last_answer else 'Нет предыдущих ответов'}\n\n"
            f"✍️ <b>Напишите ваш ответ на уточнение ниже:</b>\n"
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
