# bot/handlers/dialog_management.py
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from utils.time_utils import get_utc_now_naive

from db.qa_models import Question, User, Pharmacist
from bot.handlers.qa_states import QAStates, UserQAStates

logger = logging.getLogger(__name__)
router = Router()

# Диалоговые клавиатуры для завершения
def make_end_dialog_keyboard(question_uuid: str) -> InlineKeyboardMarkup:
    """Клавиатура для завершения диалога"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершить диалог",
                    callback_data=f"end_dialog_{question_uuid}"
                )
            ]
        ]
    )

def make_end_dialog_confirm_keyboard(question_uuid: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения завершения"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, завершить",
                    callback_data=f"confirm_end_dialog_{question_uuid}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет, продолжить",
                    callback_data=f"cancel_end_dialog_{question_uuid}"
                )
            ]
        ]
    )


async def get_active_question_for_user(user: User, db: AsyncSession) -> Optional[Question]:
    """Получить активный вопрос пользователя"""
    result = await db.execute(
        select(Question)
        .where(
            Question.user_id == user.uuid,
            Question.status.in_(["in_progress", "answered"])
        )
        .order_by(Question.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

@router.callback_query(F.data.startswith("end_dialog_"))
async def end_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    state: FSMContext,
    user: User
):
    """Предложение завершить диалог"""
    question_uuid = callback.data.replace("end_dialog_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if is_pharmacist:
            # Для фармацевта
            if question.taken_by != pharmacist.uuid:
                await callback.answer("❌ Вы не ведете этот диалог", show_alert=True)
                return

            await callback.message.answer(
                f"⚠️ <b>Завершение диалога</b>\n\n"
                f"Вы уверены, что хотите завершить диалог по вопросу?\n\n"
                f"❓ Вопрос: {question.text[:200]}...\n\n"
                f"<i>После завершения пользователь получит уведомление, "
                f"и диалог будет закрыт для ответов.</i>",
                parse_mode="HTML",
                reply_markup=make_end_dialog_confirm_keyboard(question_uuid)
            )
        else:
            # Для пользователя
            if question.user_id != user.uuid:
                await callback.answer("❌ Это не ваш вопрос", show_alert=True)
                return

            await callback.message.answer(
                f"⚠️ <b>Завершение диалога</b>\n\n"
                f"Вы уверены, что хотите завершить диалог?\n\n"
                f"❓ Ваш вопрос: {question.text[:200]}...\n\n"
                f"<i>После завершения фармацевт получит уведомление, "
                f"и вы не сможете продолжить обсуждение по этому вопросу.</i>",
                parse_mode="HTML",
                reply_markup=make_end_dialog_confirm_keyboard(question_uuid)
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in end_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при завершении диалога", show_alert=True)

# В начале функции confirm_end_dialog_callback добавьте:
@router.callback_query(F.data.startswith("confirm_end_dialog_"))
async def confirm_end_dialog_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User,
    state: FSMContext
):
    """Подтверждение завершения диалога - УЛУЧШЕННАЯ ВЕРСИЯ"""
    question_uuid = callback.data.replace("confirm_end_dialog_", "")

    try:
        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return

        if question.status in ["completed", "answered"]:
            # Показываем интуитивное сообщение для уже завершенного вопроса
            status_icon = "✅" if question.status == "completed" else "💬"
            await callback.answer(
                f"{status_icon} Этот диалог уже завершен\n"
                f"Статус: {question.status}",
                show_alert=True
            )
            return

        # Завершаем диалог
        question.status = "completed"
        question.answered_at = get_utc_now_naive()

        # Очищаем состояние
        state_data = await state.get_data()
        current_question_uuid = state_data.get("question_uuid")
        clarify_question_id = state_data.get("clarify_question_id")

        if current_question_uuid == question_uuid or clarify_question_id == question_uuid:
            await state.clear()

        await db.commit()

        if is_pharmacist:
            # Уведомляем пользователя с визуальными маркерами
            if question.user and question.user.telegram_id:
                # Получаем имя фармацевта для персонализации
                pharmacy_info = pharmacist.pharmacy_info or {}
                pharmacist_name = f"{pharmacy_info.get('first_name', '')} {pharmacy_info.get('last_name', '')}".strip()
                if not pharmacist_name:
                    pharmacist_name = "Фармацевт"

                # Создаем красивое сообщение с эмодзи
                await callback.bot.send_message(
                    chat_id=question.user.telegram_id,
                    text=(
                        "🎯 <b>КОНСУЛЬТАЦИЯ ЗАВЕРШЕНА</b>\n\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_name}\n"
                        f"📅 <b>Дата завершения:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"❓ <b>Ваш вопрос:</b>\n"
                        f"<i>{question.text[:200]}{'...' if len(question.text) > 200 else ''}</i>\n\n"
                        "✅ <b>Консультация успешно завершена!</b>\n\n"
                        "💡 <b>Что дальше?</b>\n"
                        "• Задайте новый вопрос в чате\n"
                        "• Используйте /clarify для уточнений\n"
                        "• Посмотрите историю через /my_questions\n\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "💊 <i>Спасибо, что пользуетесь нашим сервисом!</i>"
                    ),
                    parse_mode="HTML"
                )

            await callback.answer("✅ Диалог завершен!")

            # Сообщение фармацевту с визуальными маркерами
            await callback.message.answer(
                "🎯 <b>ДИАЛОГ ЗАВЕРШЕН</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ <b>Статус:</b> Консультация завершена\n"
                f"👤 <b>Пользователь:</b> Уведомлен о завершении\n"
                f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%H:%M:%S')}\n\n"
                f"❓ <b>Вопрос:</b>\n"
                f"<i>{question.text[:150]}{'...' if len(question.text) > 150 else ''}</i>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📋 Используйте /questions для новых вопросов",
                parse_mode="HTML"
            )

        else:
            # Уведомляем фармацевта
            if question.taken_by:
                pharmacist_result = await db.execute(
                    select(Pharmacist)
                    .options(selectinload(Pharmacist.user))
                    .where(Pharmacist.uuid == question.taken_by)
                )
                pharmacist_user = pharmacist_result.scalar_one_or_none()

                if pharmacist_user and pharmacist_user.user:
                    # Формируем ФИО фармацевта
                    pharmacy_info = pharmacist_user.pharmacy_info or {}
                    pharmacist_name = f"{pharmacy_info.get('first_name', '')} {pharmacy_info.get('last_name', '')}".strip()
                    if not pharmacist_name:
                        pharmacist_name = "Фармацевт"

                    await callback.bot.send_message(
                        chat_id=pharmacist_user.user.telegram_id,
                        text=(
                            "🎯 <b>ПОЛЬЗОВАТЕЛЬ ЗАВЕРШИЛ ДИАЛОГ</b>\n\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 <b>Пользователь:</b> {user.first_name or 'Пользователь'}\n"
                            f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%d.%m.%Y %H:%M')}\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"❓ <b>Вопрос:</b>\n"
                            f"<i>{question.text[:200]}{'...' if len(question.text) > 200 else ''}</i>\n\n"
                            "✅ <b>Диалог завершен по инициативе пользователя</b>\n\n"
                            "💡 <b>Статус:</b> Консультация завершена\n"
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "📋 Используйте /questions для новых вопросов"
                        ),
                        parse_mode="HTML"
                    )

            await callback.answer("✅ Диалог завершен!")

            # Сообщение пользователю с визуальными маркерами
            await callback.message.answer(
                "🎯 <b>ВАША КОНСУЛЬТАЦИЯ ЗАВЕРШЕНА</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ <b>Статус:</b> Консультация завершена\n"
                f"👨‍⚕️ <b>Фармацевт:</b> Уведомлен о завершении\n"
                f"📅 <b>Время:</b> {get_utc_now_naive().strftime('%H:%M:%S')}\n\n"
                f"❓ <b>Ваш вопрос:</b>\n"
                f"<i>{question.text[:150]}{'...' if len(question.text) > 150 else ''}</i>\n\n"
                "💡 <b>Что дальше?</b>\n"
                "• Просто напишите новый вопрос в чат\n"
                "• Или нажмите /ask для быстрого старта\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💊 <i>Спасибо за использование нашего сервиса!</i>",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in confirm_end_dialog_callback: {e}")
        await callback.answer("❌ Ошибка при завершении диалога", show_alert=True)

@router.callback_query(F.data.startswith("cancel_end_dialog_"))
async def cancel_end_dialog_callback(
    callback: CallbackQuery,
    is_pharmacist: bool,
    state: FSMContext
):
    """Отмена завершения диалога"""
    await callback.answer("❌ Завершение диалога отменено")

    state_data = await state.get_data()
    current_question = state_data.get("question_uuid")

    if is_pharmacist:
        await callback.message.answer(
            "🔄 Продолжайте диалог с пользователем.\n"
            f"Используйте /questions для просмотра других вопросов."
        )
    else:
        # Если у пользователя есть активный вопрос, показываем соответствующее сообщение
        if current_question:
            await callback.message.answer(
                "🔄 Диалог продолжается.\n"
                "Вы можете задать уточняющий вопрос или отправить фото."
            )
        else:
            await callback.message.answer(
                "🔄 Вы можете задать новый вопрос, просто напишите его в чат!"
            )

@router.message(Command("end_dialog"))
async def cmd_end_dialog(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
    user: User
):
    """Команда для завершения диалога"""
    try:
        if is_pharmacist:
            # Получаем активные вопросы фармацевта
            result = await db.execute(
                select(Question)
                .where(
                    Question.taken_by == pharmacist.uuid,
                    Question.status.in_(["in_progress", "answered"])
                )
                .order_by(Question.taken_at.desc())
            )
            questions = result.scalars().all()
        else:
            # Получаем активные вопросы пользователя
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
                "📭 У вас нет активных диалогов для завершения."
            )
            return

        # Создаем клавиатуру с вопросами для завершения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for question in questions[:5]:
            question_preview = question.text[:50] + "..." if len(question.text) > 50 else question.text
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"❓ {question_preview}",
                    callback_data=f"end_dialog_{question.uuid}"
                )
            ])

        await message.answer(
            "📋 <b>Выберите диалог для завершения:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in cmd_end_dialog: {e}")
        await message.answer("❌ Ошибка при получении диалогов")
