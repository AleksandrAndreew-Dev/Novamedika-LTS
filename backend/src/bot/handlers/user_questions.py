from aiogram.types import Message as AiogramMessage
from typing import Union, List
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


async def get_all_user_questions(
    db: AsyncSession, user: User, limit: int = 50
) -> List[Question]:
    """Получить все вопросы пользователя с пагинацией"""
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.user))
        .where(Question.user_id == user.uuid)
        .order_by(Question.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def format_questions_list(
    questions: List[Question], page: int = 0, per_page: int = 10
) -> str:
    """Форматировать список вопросов для отображения"""
    start_idx = page * per_page
    end_idx = start_idx + per_page

    message_text = f"📋 <b>ВАШИ ВОПРОСЫ</b>\n\n"

    if not questions:
        return (
            message_text
            + "📭 У вас пока нет вопросов.\n\nЗадайте первый вопрос, просто написав его в чат."
        )

    # Показываем вопросы на текущей странице
    for i, question in enumerate(questions[start_idx:end_idx], start_idx + 1):
        status_icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "answered": "💬",
            "completed": "✅",
        }
        icon = status_icons.get(question.status, "❓")
        time_str = question.created_at.strftime("%d.%m.%Y %H:%M")

        # Обрезаем длинный текст
        question_preview = question.text[:80]
        if len(question.text) > 80:
            question_preview += "..."

        message_text += f"{icon} <b>Вопрос #{i}:</b>\n"
        message_text += f"📅 {time_str}\n"
        message_text += f"📝 {question_preview}\n"
        message_text += f"📊 Статус: {question.status.replace('_', ' ').title()}\n\n"

    # Информация о пагинации
    total = len(questions)
    total_pages = (total + per_page - 1) // per_page

    if total_pages > 1:
        message_text += f"📄 Страница {page + 1} из {total_pages} "
        message_text += f"(всего {total} вопросов)\n\n"

    return message_text


def make_questions_pagination_keyboard(
    questions: List[Question],
    page: int = 0,
    per_page: int = 10,
    include_back: bool = True,
) -> InlineKeyboardMarkup:
    """Создать клавиатуру пагинации для списка вопросов"""
    total = len(questions)
    total_pages = (total + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total)

    keyboard = []

    # Кнопки для вопросов на текущей странице
    for i, question in enumerate(questions[start_idx:end_idx], start_idx):
        question_preview = (
            question.text[:40] + "..." if len(question.text) > 40 else question.text
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📋 Вопрос #{i+1}: {question_preview}",
                    callback_data=f"view_full_history_{question.uuid}",
                )
            ]
        )

    # Кнопки пагинации
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"questions_page_{page-1}"
            )
        )

    pagination_buttons.append(
        InlineKeyboardButton(
            text=f"{page+1}/{total_pages}", callback_data="current_page"
        )
    )

    if page < total_pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", callback_data=f"questions_page_{page+1}"
            )
        )

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    # Кнопки фильтрации
    filter_buttons = []
    filter_buttons.append(
        InlineKeyboardButton(text="🎯 Активные", callback_data="filter_active")
    )
    filter_buttons.append(
        InlineKeyboardButton(text="✅ Завершенные", callback_data="filter_completed")
    )
    keyboard.append(filter_buttons)

    # Кнопка возврата
    if include_back:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 В главное меню", callback_data="back_to_main"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
    """Показать все вопросы пользователя с пагинацией"""
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
            # Для фармацевтов - активные диалоги (оставляем старую логику)
            result = await db.execute(
                select(Question)
                .where(
                    Question.taken_by == user.uuid,
                    Question.status.in_(["in_progress", "answered"]),
                )
                .order_by(Question.taken_at.desc())
            )
            questions = result.scalars().all()

            if not questions:
                await message.answer(
                    "📭 У вас нет активных диалогов.\n\n"
                    "Используйте /questions для просмотра новых вопросов."
                )
                if is_callback:
                    await update.answer()
                return

            # Показываем фармацевтам только активные диалоги
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])

            for i, question in enumerate(questions[:10], 1):
                status_icon = "💬" if question.status == "answered" else "🔄"
                question_preview = (
                    question.text[:50] + "..."
                    if len(question.text) > 50
                    else question.text
                )

                keyboard.inline_keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=f"{status_icon} Диалог #{i}: {question_preview}",
                            callback_data=f"view_dialog_{question.uuid}",
                        )
                    ]
                )

            await message.answer(
                f"💬 <b>ВАШИ АКТИВНЫЕ ДИАЛОГИ</b>\n\n"
                f"Всего активных диалогов: {len(questions)}\n\n"
                f"Выберите диалог для просмотра:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:
            # ДЛЯ ПОЛЬЗОВАТЕЛЕЙ - НОВАЯ ЛОГИКА
            questions = await get_all_user_questions(db, user, limit=50)
            page = 0  # Начинаем с первой страницы

            message_text = await format_questions_list(questions, page)
            reply_markup = make_questions_pagination_keyboard(questions, page)

            await message.answer(
                message_text, parse_mode="HTML", reply_markup=reply_markup
            )

        if is_callback:
            await update.answer()

    except Exception as e:
        logger.error(f"Error in cmd_my_questions: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении вопросов")


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
        # Получаем вопрос
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

        # Получаем полную историю диалога
        from bot.services.dialog_service import DialogService

        history_text, file_ids = await DialogService.format_dialog_history_for_display(
            question_uuid, db, limit=50  # Большой лимит для полной истории
        )

        # Формируем заголовок с информацией о вопросе
        status_info = {
            "pending": "⏳ Ожидает ответа",
            "in_progress": "🔄 В обработке",
            "answered": "💬 Отвечен",
            "completed": "✅ Завершен",
        }

        status_text = status_info.get(question.status, "❓ Неизвестный статус")
        created_time = question.created_at.strftime("%d.%m.%Y %H:%M")

        # Получаем информацию о фармацевте, если есть
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

        # Создаем клавиатуру с действиями
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    (
                        InlineKeyboardButton(
                            text="✍️ Уточнить вопрос",
                            callback_data=f"quick_clarify_{question.uuid}",
                        )
                        if question.status == "answered"
                        else None
                    ),
                    (
                        InlineKeyboardButton(
                            text="📸 Отправить фото",
                            callback_data=f"send_prescription_photo_{question.uuid}",
                        )
                        if question.context_data
                        and question.context_data.get("photo_requested")
                        else None
                    ),
                ],
                [
                    (
                        InlineKeyboardButton(
                            text="✅ Завершить консультацию",
                            callback_data=f"end_dialog_{question.uuid}",
                        )
                        if question.status in ["answered", "in_progress"]
                        else None
                    ),
                    (
                        InlineKeyboardButton(
                            text="🔄 Продолжить общение",
                            callback_data=f"continue_dialog_{question.uuid}",
                        )
                        if question.status == "in_progress"
                        else None
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 К списку вопросов", callback_data="back_to_questions"
                    ),
                    InlineKeyboardButton(
                        text="📋 Скопировать историю",
                        callback_data=f"export_history_{question.uuid}",
                    ),
                ],
            ]
        )

        # Удаляем пустые кнопки
        keyboard.inline_keyboard = [row for row in keyboard.inline_keyboard if any(row)]

        # Отправляем сообщение
        if len(full_message) > 4096:
            # Разбить на части
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

        # Если есть фото, отправляем их отдельно
        if file_ids:
            await callback.message.answer(
                "📸 <b>Фото из истории диалога:</b>", parse_mode="HTML"
            )
            for file_id in file_ids[:5]:  # Ограничиваем 5 фото
                try:
                    await callback.message.answer_photo(file_id, caption=" ")
                except Exception as e:
                    logger.error(f"Error sending photo: {e}")
                    await callback.message.answer("⚠️ Не удалось отправить одно из фото")

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view_full_history_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке истории", show_alert=True)


# ДОБАВЛЯЕМ ОБРАБОТЧИКИ ПАГИНАЦИИ И ФИЛЬТРАЦИИ
@router.callback_query(F.data.startswith("questions_page_"))
async def questions_page_callback(
    callback: CallbackQuery, db: AsyncSession, user: User, is_pharmacist: bool
):
    """Обработка переключения страниц"""
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    page = int(callback.data.replace("questions_page_", ""))

    try:
        questions = await get_all_user_questions(db, user, limit=50)

        if not questions:
            await callback.answer("📭 У вас пока нет вопросов", show_alert=True)
            return

        message_text = await format_questions_list(questions, page)
        reply_markup = make_questions_pagination_keyboard(questions, page)

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
    if is_pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только пользователям", show_alert=True
        )
        return

    try:
        questions = await get_all_user_questions(db, user, limit=50)
        page = 0

        message_text = await format_questions_list(questions, page)
        reply_markup = make_questions_pagination_keyboard(questions, page)

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
        # Получаем все вопросы
        result = await db.execute(
            select(Question)
            .where(Question.user_id == user.uuid)
            .order_by(Question.created_at.desc())
        )
        all_questions = result.scalars().all()

        # Фильтруем вопросы
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

        # Форматируем первые 10 вопросов
        for i, question in enumerate(questions[:10], 1):
            status_icons = {
                "pending": "⏳",
                "in_progress": "🔄",
                "answered": "💬",
                "completed": "✅",
            }
            icon = status_icons.get(question.status, "❓")
            time_str = question.created_at.strftime("%d.%m.%Y %H:%M")

            question_preview = question.text[:60]
            if len(question.text) > 60:
                question_preview += "..."

            message_text += f"{icon} <b>Вопрос #{i}:</b>\n"
            message_text += f"📅 {time_str}\n"
            message_text += f"📝 {question_preview}\n\n"

        # Создаем клавиатуру с отфильтрованными вопросами
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

        # Кнопки фильтрации
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


# ДОБАВЛЯЕМ ОБРАБОТЧИК ДЛЯ ЭКСПОРТА ИСТОРИИ
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
        # Получаем вопрос
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        # Получаем историю диалога
        from bot.services.dialog_service import DialogService

        history_messages = await DialogService.get_dialog_history(
            question.uuid, db, limit=100
        )

        # Форматируем для экспорта
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

        # Сохраняем во временный файл или отправляем как текст
        if len(export_text) <= 4096:
            await callback.message.answer(
                f"📄 <b>Экспорт истории консультации:</b>\n\n"
                f"<code>{export_text}</code>",
                parse_mode="HTML",
            )
        else:
            # Если текст слишком длинный, разбиваем на части
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


# ДОБАВЛЯЕМ ОБРАБОТЧИК ДЛЯ ПРОДОЛЖЕНИЯ ДИАЛОГА
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
        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if question.status != "in_progress":
            await callback.answer(
                "❌ Этот диалог уже завершен или ожидает ответа", show_alert=True
            )
            return

        # Устанавливаем состояние для продолжения диалога
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
        await message.answer(
            "❌ Вопрос не может быть пустым. Пожалуйста, напишите текст вопроса."
        )
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
        await DialogService.create_question_message(question, db)

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
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    is_pharmacist: bool,
):
    """Обработка сообщений пользователя в активном диалоге"""
    if is_pharmacist:
        await message.answer("👨‍⚕️ Вы фармацевт. Используйте /questions для ответов.")
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("active_dialog_question_id")

        if not question_uuid:
            await message.answer(
                "❌ Не найден активный диалог. "
                "Используйте /my_questions для продолжения."
            )
            await state.clear()
            return

        # Получаем вопрос
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or question.user_id != user.uuid:
            await message.answer("❌ Диалог не найден или недоступен.")
            await state.clear()
            return

        # Получаем фармацевта, который ведет диалог
        if not question.taken_by:
            await message.answer("❌ Фармацевт не назначен для этого диалога.")
            return

        pharmacist_result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == question.taken_by)
        )
        pharmacist = pharmacist_result.scalar_one_or_none()

        if not pharmacist or not pharmacist.user:
            await message.answer("❌ Фармацевт не найден.")
            return

        # Добавляем сообщение в историю диалога
        await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="message",
            text=message.text,
        )
        await db.commit()

        # Получаем историю диалога для контекста
        history_text, _ = await DialogService.format_dialog_history_for_display(
            question.uuid, db, limit=10
        )

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

        # Создаем клавиатуру для фармацевта
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        pharmacist_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Ответить пользователю",
                        callback_data=f"answer_{question.uuid}",
                    ),
                    InlineKeyboardButton(
                        text="📸 Запросить фото",
                        callback_data=f"request_photo_{question.uuid}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Завершить диалог",
                        callback_data=f"end_dialog_{question.uuid}",
                    )
                ],
            ]
        )

        # Отправляем сообщение фармацевту
        await message.bot.send_message(
            chat_id=pharmacist.user.telegram_id,
            text=f"💬 <b>СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_name}\n"
            f"❓ <b>По вопросу:</b>\n{question.text[:150]}...\n\n"
            f"💭 <b>Сообщение:</b>\n{message.text}\n\n"
            f"{history_text}",
            parse_mode="HTML",
            reply_markup=pharmacist_keyboard,
        )

        # Подтверждаем пользователю
        await message.answer(
            f"✅ Сообщение отправлено фармацевту {pharmacist_name}.\n\n"
            "Вы можете продолжить общение или завершить диалог.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💬 Продолжить общение",
                            callback_data=f"continue_user_dialog_{question.uuid}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ Завершить консультацию",
                            callback_data=f"end_dialog_{question.uuid}",
                        )
                    ],
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Error in process_dialog_message: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке сообщения. Попробуйте еще раз.")


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

        # Создаем клавиатуру для фармацевта
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        pharmacist_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Ответить пользователю",
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

        # Отправляем фото с подписью и историей С КНОПКАМИ
        await message.bot.send_photo(
            chat_id=pharmacist.user.telegram_id,
            photo=photo.file_id,
            caption=f"📸 <b>Получено фото рецепта</b>\n\n"
            f"👤 <b>От пользователя:</b> {user_name}\n"
            f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"{history_text}",
            parse_mode="HTML",
            reply_markup=pharmacist_keyboard,
        )

        # Показываем пользователю подтверждение С КНОПКАМИ
        await message.answer(
            f"✅ Фото рецепта отправлено фармацевту!\n\n"
            f"📸 <b>Фото добавлено в историю диалога.</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✍️ Уточнить вопрос",
                            callback_data=f"quick_clarify_{question_uuid}",
                        ),
                        InlineKeyboardButton(
                            text="✅ Завершить консультацию",
                            callback_data=f"end_dialog_{question_uuid}",
                        ),
                    ]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Error processing prescription photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке фото")


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
