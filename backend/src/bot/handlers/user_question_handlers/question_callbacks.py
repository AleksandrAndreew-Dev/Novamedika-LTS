"""Callback-обработчики списка вопросов: история, пагинация, фильтры, экспорт, продолжение."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.qa_models import User, Question, Pharmacist
from bot.handlers.qa_states import UserQAStates
from bot.keyboards.qa_keyboard import get_post_consultation_keyboard
from bot.keyboards.pagination_keyboard import make_questions_pagination_keyboard
from bot.services.dialog_service import DialogService
from bot.handlers.user_question_handlers.commands import (
    get_all_user_questions,
    format_questions_list,
)
from src.utils.get_utils import get_all_pharmacist_questions
from src.utils.pharm_format_questions import format_pharmacist_questions_list

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("view_full_history_"))
async def view_full_history_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
    state: FSMContext,
):
    """Просмотр полной истории консультации"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("view_full_history_", "")

    try:
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer(
                "❌ Вопрос не найден или не принадлежит вам", show_alert=True
            )
            return

        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question_uuid, db, limit=50
        )

        status_info = {
            "pending": "⏳ Ожидает ответа",
            "in_progress": "🔄 В обработке",
            "answered": "💬 Отвечен",
            "completed": "✅ Завершен",
        }
        status_text = status_info.get(question.status, "❓ Неизвестный статус")
        created_time = question.created_at.strftime("%d.%m.%Y %H:%M")

        pharmacist_info = ""
        if question.taken_by:
            pharmacist_result = await db.execute(
                select(Pharmacist).where(Pharmacist.uuid == question.taken_by)
            )
            pharmacist = pharmacist_result.scalar_one_or_none()

            if pharmacist and pharmacist.pharmacy_info:
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
                pharmacist_info = f"\n👨‍⚕️ <b>Фармацевт:</b> {pharmacist_name}"

        full_message = (
            f"📚 <b>ПОЛНАЯ ИСТОРИЯ КОНСУЛЬТАЦИИ</b>\n\n"
            f"📅 <b>Дата создания:</b> {created_time}\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"{pharmacist_info}\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{history_text}"
        )

        inline_keyboard = []

        first_row = []
        if question.status == "answered":
            first_row.append(
                InlineKeyboardButton(
                    text="✍️ Уточнить вопрос",
                    callback_data=f"quick_clarify_{question.uuid}",
                )
            )
        if question.context_data and question.context_data.get("photo_requested"):
            first_row.append(
                InlineKeyboardButton(
                    text="📸 Отправить фото",
                    callback_data=f"send_prescription_photo_{question.uuid}",
                )
            )
        if first_row:
            inline_keyboard.append(first_row)

        second_row = []
        if question.status in ["answered", "in_progress"]:
            second_row.append(
                InlineKeyboardButton(
                    text="✅ Завершить консультацию",
                    callback_data=f"end_dialog_{question.uuid}",
                )
            )
        if question.status == "in_progress":
            second_row.append(
                InlineKeyboardButton(
                    text="🔄 Продолжить общение",
                    callback_data=f"continue_dialog_{question.uuid}",
                )
            )
        if second_row:
            inline_keyboard.append(second_row)

        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 К списку вопросов", callback_data="back_to_questions"
                ),
                InlineKeyboardButton(
                    text="📋 Скопировать историю",
                    callback_data=f"export_history_{question.uuid}",
                ),
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        if len(full_message) > 4096:
            parts = [
                full_message[i : i + 4000] for i in range(0, len(full_message), 4000)
            ]
            for i, part in enumerate(parts, 1):
                if i == 1:
                    await callback.message.answer(
                        part + f"\n\n(Часть {i}/{len(parts)})",
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    await callback.message.answer(
                        part + f"\n\n(Часть {i}/{len(parts)})", parse_mode="HTML"
                    )
        else:
            await callback.message.answer(
                full_message, parse_mode="HTML", reply_markup=keyboard
            )

        if file_ids:
            await callback.message.answer(
                "📸 <b>Фото из истории диалога:</b>", parse_mode="HTML"
            )
            for file_id in file_ids[:5]:
                try:
                    await callback.message.answer_photo(file_id, caption=" ")
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")
                    await callback.message.answer("⚠️ Не удалось отправить одно из фото")

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_full_history_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке истории", show_alert=True)


@router.callback_query(F.data.startswith("questions_page_"))
async def questions_page_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Обработка переключения страниц"""
    page = int(callback.data.replace("questions_page_", ""))

    try:
        if is_pharmacist:
            result = await db.execute(
                select(Pharmacist).where(Pharmacist.user_id == user.uuid)
            )
            pharmacist = result.scalar_one_or_none()

            if not pharmacist:
                await callback.answer("❌ Вы не найдены как фармацевт", show_alert=True)
                return

            questions = await get_all_pharmacist_questions(db, pharmacist, limit=50)
            message_text = await format_pharmacist_questions_list(questions, page)
        else:
            questions = await get_all_user_questions(db, user, limit=50)
            message_text = await format_questions_list(questions, page)

        if not questions:
            await callback.answer("📭 У вас пока нет вопросов", show_alert=True)
            return

        reply_markup = make_questions_pagination_keyboard(
            questions,
            page,
            is_pharmacist=is_pharmacist,
            pharmacist_id=(
                str(pharmacist.uuid) if is_pharmacist and pharmacist else None
            ),
        )

        await callback.message.edit_text(
            message_text, parse_mode="HTML", reply_markup=reply_markup
        )
        await callback.answer(f"Страница {page + 1}")

    except Exception as e:
        logger.error(f"Error in questions_page_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при переключении страницы", show_alert=True)


@router.callback_query(F.data == "back_to_questions")
async def back_to_questions_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Возврат к списку вопросов"""
    try:
        if is_pharmacist:
            result = await db.execute(
                select(Pharmacist).where(Pharmacist.user_id == user.uuid)
            )
            pharmacist = result.scalar_one_or_none()

            if not pharmacist:
                await callback.answer("❌ Вы не найдены как фармацевт", show_alert=True)
                return

            questions = await get_all_pharmacist_questions(db, pharmacist, limit=50)
            message_text = await format_pharmacist_questions_list(questions, page=0)
        else:
            questions = await get_all_user_questions(db, user, limit=50)
            message_text = await format_questions_list(questions, page=0)

        reply_markup = make_questions_pagination_keyboard(
            questions,
            page=0,
            is_pharmacist=is_pharmacist,
            pharmacist_id=(
                str(pharmacist.uuid) if is_pharmacist and pharmacist else None
            ),
        )

        await callback.message.edit_text(
            message_text, parse_mode="HTML", reply_markup=reply_markup
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_questions_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при возврате к списку", show_alert=True)


@router.callback_query(F.data.startswith("filter_"))
async def filter_questions_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Фильтрация вопросов по статусу"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    filter_type = callback.data.replace("filter_", "")

    try:
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid)
            .order_by(Question.created_at.desc())
        )
        all_questions = result.scalars().all()

        if filter_type == "active":
            questions = [q for q in all_questions if q.status != "completed"]
            filter_text = "активные"
        elif filter_type == "completed":
            questions = [q for q in all_questions if q.status == "completed"]
            filter_text = "завершенные"
        else:
            questions = all_questions
            filter_text = "все"

        if not questions:
            await callback.answer(
                f"📭 У вас нет {filter_text} вопросов", show_alert=True
            )
            return

        message_text = f"📋 <b>ВАШИ ВОПРОСЫ ({filter_text.title()})</b>\n\n"
        message_text += f"Найдено: {len(questions)} вопросов\n\n"

        for i, question in enumerate(questions[:10], 1):
            status_icons = {
                "pending": "⏳",
                "in_progress": "🔄",
                "answered": "💬",
                "completed": "✅",
            }
            icon = status_icons.get(question.status, "❓")
            time_str = question.created_at.strftime("%d.%m.%Y %H:%M")
            question_preview = (
                question.text[:60] + "..." if len(question.text) > 60 else question.text
            )

            message_text += f"{icon} <b>Вопрос #{i}:</b>\n"
            message_text += f"📅 {time_str}\n"
            message_text += f"📝 {question_preview}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for i, question in enumerate(questions[:10], 1):
            question_preview = (
                question.text[:40] + "..." if len(question.text) > 40 else question.text
            )
            status_icon = "✅" if question.status == "completed" else "💬"

            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"{status_icon} Вопрос #{i}: {question_preview}",
                        callback_data=f"view_full_history_{question.uuid}",
                    )
                ]
            )

        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(text="🎯 Активные", callback_data="filter_active"),
                InlineKeyboardButton(
                    text="✅ Завершенные", callback_data="filter_completed"
                ),
                InlineKeyboardButton(
                    text="📋 Все", callback_data="my_questions_callback"
                ),
            ]
        )
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 В главное меню", callback_data="back_to_main"
                )
            ]
        )

        await callback.message.edit_text(
            message_text, parse_mode="HTML", reply_markup=keyboard
        )
        await callback.answer(f"Показаны {filter_text} вопросы")

    except Exception as e:
        logger.error(f"Error in filter_questions_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при фильтрации", show_alert=True)


@router.callback_query(F.data.startswith("export_history_"))
async def export_history_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Экспорт истории консультации в текстовый формат"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("export_history_", "")

    try:
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        history_messages = await DialogService.get_dialog_history(
            question.uuid, db, limit=100
        )

        export_text = (
            f"КОНСУЛЬТАЦИЯ ОТ {question.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        export_text += "=" * 50 + "\n\n"
        export_text += f"ВОПРОС: {question.text}\n\n"
        export_text += "ИСТОРИЯ ДИАЛОГА:\n"
        export_text += "-" * 30 + "\n\n"

        for msg in history_messages:
            sender = "Вы" if msg.sender_type == "user" else "Фармацевт"
            time_str = msg.created_at.strftime("%H:%M")

            if msg.message_type == "question":
                export_text += f"[{time_str}] {sender}: ❓ {msg.text}\n"
            elif msg.message_type == "answer":
                export_text += f"[{time_str}] {sender}: 💬 {msg.text}\n"
            elif msg.message_type == "clarification":
                export_text += f"[{time_str}] {sender}: 🔍 {msg.text}\n"
            elif msg.message_type == "photo":
                export_text += f"[{time_str}] {sender}: 📸 Фото рецепта\n"
            else:
                export_text += f"[{time_str}] {sender}: 💭 {msg.text}\n"

            if msg.caption:
                export_text += f"    Описание: {msg.caption}\n"

        export_text += "\n" + "=" * 50 + "\n"
        export_text += f"Статус: {question.status.upper()}\n"
        export_text += f"Завершено: {question.answered_at.strftime('%d.%m.%Y %H:%M') if question.answered_at else 'Не завершено'}"

        if len(export_text) <= 4096:
            await callback.message.answer(
                f"📄 <b>Экспорт истории консультации:</b>\n\n"
                f"<code>{export_text}</code>",
                parse_mode="HTML",
            )
        else:
            parts = [
                export_text[i : i + 4000] for i in range(0, len(export_text), 4000)
            ]
            for i, part in enumerate(parts, 1):
                await callback.message.answer(
                    f"📄 <b>Часть {i} из {len(parts)}:</b>\n\n" f"<code>{part}</code>",
                    parse_mode="HTML",
                )

        await callback.answer("✅ История экспортирована")

    except Exception as e:
        logger.error(f"Error in export_history_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при экспорте", show_alert=True)


@router.callback_query(F.data.startswith("continue_dialog_"))
async def continue_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Продолжить общение по существующему вопросу"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    question_uuid = callback.data.replace("continue_dialog_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if question.status == "completed":
            await callback.answer("❌ Консультация завершена", show_alert=True)
            await callback.message.answer(
                f"🎯 <b>Консультация завершена</b>\n\n"
                f"Вопрос: {question.text[:200]}...\n\n"
                "Вы можете:",
                parse_mode="HTML",
                reply_markup=get_post_consultation_keyboard(),
            )
            return

        if question.status != "in_progress":
            await callback.answer(
                "❌ Этот диалог уже завершен или ожидает ответа", show_alert=True
            )
            return

        await state.update_data(continue_question_id=question_uuid)
        await state.set_state(UserQAStates.in_dialog)

        await callback.message.answer(
            "💬 <b>ПРОДОЛЖЕНИЕ ДИАЛОГА</b>\n\n"
            f"❓ <b>Ваш вопрос:</b>\n{question.text}\n\n"
            "Напишите ваше сообщение для фармацевта:\n"
            "(или /done для завершения диалога)",
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in continue_dialog_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при продолжении диалога", show_alert=True)
