"""Обработчики запроса фото рецепта от фармацевта."""

import logging

from aiogram import F, Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from utils.time_utils import get_utc_now_naive
from db.qa_models import Pharmacist, Question
from bot.handlers.qa_states import QAStates
from bot.keyboards.qa_keyboard import make_pharmacist_dialog_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("request_photo_"))
async def request_photo_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка запроса фото рецепта от фармацевта"""
    question_uuid = callback.data.replace("request_photo_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

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

        if question.taken_by != pharmacist.uuid and question.status == "in_progress":
            await callback.answer(
                "❌ Этот вопрос уже взят другим фармацевтом", show_alert=True
            )
            return

        if question.status == "pending":
            question.taken_by = pharmacist.uuid
            question.taken_at = get_utc_now_naive()
            question.status = "in_progress"

        if not question.context_data:
            question.context_data = {}

        question.context_data["photo_requested_by"] = {
            "pharmacist_id": str(pharmacist.uuid),
            "telegram_id": pharmacist.user.telegram_id,
            "requested_at": get_utc_now_naive().isoformat(),
        }
        question.context_data["photo_requested"] = True
        await db.commit()

        await state.update_data(question_uuid=question_uuid)
        await callback.answer("✅ Запрос фото отправлен пользователю!")

        if question.user and question.user.telegram_id:
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

            await callback.bot.send_message(
                chat_id=question.user.telegram_id,
                text=f"📸 <b>Фармацевту запросил фото рецепта</b>\n\n"
                f"Вопрос: {question.text[:200]}...\n\n"
                "Нажмите кнопку ниже:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📸 Отправить фото",
                                callback_data=f"send_prescription_photo_{question.uuid}",
                            )
                        ]
                    ]
                ),
            )

        await callback.message.answer(
            f"📸 <b>Запрос фото рецепта отправлен</b>\n\n"
            f"Пользователь получил уведомление о необходимости отправить фото.\n\n"
            f"Продолжайте диалог:",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )

    except Exception as e:
        logger.error(f"Error in request_photo_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.callback_query(F.data.startswith("request_more_photos_"))
async def request_more_photos_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Запросить еще фото рецепта"""
    question_uuid = callback.data.replace("request_more_photos_", "")

    if not is_pharmacist or not pharmacist:
        await callback.answer(
            "❌ Эта функция доступна только фармацевтам", show_alert=True
        )
        return

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

        if not question.context_data:
            question.context_data = {}

        question.context_data["photo_requested_by"] = {
            "pharmacist_id": str(pharmacist.uuid),
            "telegram_id": pharmacist.user.telegram_id,
            "requested_at": get_utc_now_naive().isoformat(),
        }
        question.context_data["photo_requested"] = True
        await db.commit()

        photo_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📸 Отправить еще фото рецепта",
                        callback_data=f"send_prescription_photo_{question.uuid}",
                    )
                ]
            ]
        )

        await callback.bot.send_message(
            chat_id=question.user.telegram_id,
            text=f"📸 <b>Фармацевт запросил дополнительное фото рецепта</b>\n\n"
            f"❓ <b>По вопросу:</b>\n{question.text}\n\n"
            f"Пожалуйста, отправьте еще фото рецепта:",
            parse_mode="HTML",
            reply_markup=photo_keyboard,
        )

        await callback.answer(
            "✅ Запрос на дополнительное фото отправлен пользователю!"
        )

        await callback.message.answer(
            "📸 Запрос на дополнительное фото отправлен пользователю.\n\n"
            "Продолжайте диалог:",
            reply_markup=make_pharmacist_dialog_keyboard(question_uuid),
        )

    except Exception as e:
        logger.error(f"Error in request_more_photos_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


@router.message(QAStates.waiting_for_photo_request)
async def process_photo_request_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка сообщения для запроса фото рецепта"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("photo_request_question_id")
        original_message_id = state_data.get("photo_request_message_id")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос")
            await state.clear()
            return

        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user))
            .where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question or not question.user:
            await message.answer("❌ Вопрос или пользователь не найдены")
            await state.clear()
            return

        if not question.context_data:
            question.context_data = {}
        question.context_data["photo_requested"] = True
        await db.commit()

        if question.context_data and question.context_data.get("is_clarification"):
            original_question_id = question.context_data.get("original_question_id")
            if original_question_id:
                original_result = await db.execute(
                    select(Question).where(Question.uuid == original_question_id)
                )
                original_question = original_result.scalar_one_or_none()
                if original_question:
                    if not original_question.context_data:
                        original_question.context_data = {}
                    original_question.context_data["photo_requested_by"] = {
                        "pharmacist_id": str(pharmacist.uuid),
                        "telegram_id": pharmacist.user.telegram_id,
                        "requested_at": get_utc_now_naive().isoformat(),
                    }
                    original_question.context_data["photo_requested"] = True
                await db.commit()

        pharmacy_info = pharmacist.pharmacy_info or {}
        first_name = pharmacy_info.get("first_name", "")
        last_name = pharmacy_info.get("last_name", "")
        patronymic = pharmacy_info.get("patronymic", "")

        pharmacist_name_parts = []
        if last_name:
            pharmacist_name_parts.append(last_name)
        if first_name:
            pharmacist_name_parts.append(first_name)
        if patronymic:
            pharmacist_name_parts.append(patronymic)

        pharmacist_name = (
            " ".join(pharmacist_name_parts) if pharmacist_name_parts else "Фармацевт"
        )

        photo_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📸 Отправить фото рецепта",
                        callback_data=f"send_prescription_photo_{question.uuid}",
                    )
                ]
            ]
        )

        await message.bot.send_message(
            chat_id=question.user.telegram_id,
            text=f"📸 <b>Фармацевт запросил фото рецепта</b>\n\n"
            f"👨‍⚕️ <b>Фармацевт:</b> {pharmacist_name}\n\n"
            f"💬 <b>Сообщение:</b>\n{message.text}\n\n"
            f"❓ <b>По вопросу:</b>\n{question.text}\n\n"
            f"Нажмите кнопку ниже, чтобы отправить фото рецепта:",
            parse_mode="HTML",
            reply_markup=photo_keyboard,
        )

        await message.answer(
            "✅ Запрос на фото рецепта отправлен пользователю!\n\n"
            "Вы получите уведомление, когда пользователь отправит фото."
        )

        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=original_message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        await state.clear()

    except Exception as e:
        logger.error(f"Error in process_photo_request_message: {e}", exc_info=True)
        await message.answer("❌ Ошибка при отправке запроса")
        await state.clear()
