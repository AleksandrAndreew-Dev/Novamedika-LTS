"""Обработчики текстовых сообщений в диалоге фармацевта."""

import logging

from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.time_utils import get_utc_now_naive
from db.qa_models import User, Pharmacist, Question, Answer
from bot.handlers.qa_states import QAStates
from bot.keyboards.qa_keyboard import make_pharmacist_dialog_keyboard
from bot.services.dialog_service import DialogService

logger = logging.getLogger(__name__)

router = Router()


@router.message(QAStates.in_dialog_with_user, F.text)
async def handle_pharmacist_text_in_dialog(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка текстовых сообщений фармацевта в диалоге"""
    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        if question.status == "completed":
            await message.answer(
                "❌ Этот диалог уже завершен. Вы не можете отправлять сообщения.\n"
                "Используйте /questions для работы с новыми вопросами."
            )
            await state.clear()
            return

        if not pharmacist.is_online:
            pharmacist.is_online = True
            pharmacist.last_seen = get_utc_now_naive()
            await db.commit()

        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )
        db.add(answer)

        if question.status != "completed":
            question.status = "answered"
        question.answered_at = get_utc_now_naive()
        question.answered_by = pharmacist.uuid

        await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="pharmacist",
            sender_id=pharmacist.uuid,
            message_type="answer",
            text=message.text,
        )
        await db.commit()

        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            try:
                pharmacy_info = pharmacist.pharmacy_info or {}
                chain = pharmacy_info.get("chain", "Не указана")
                number = pharmacy_info.get("number", "Не указан")
                role = pharmacy_info.get("role", "Фармацевт")

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
                    " ".join(pharmacist_name_parts)
                    if pharmacist_name_parts
                    else "Фармацевт"
                )
                pharmacist_info_text = f"{pharmacist_name}"

                if chain and number:
                    pharmacist_info_text += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info_text += f" ({role})"

                user_dialog_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✍️ Ответить фармацевту",
                                callback_data=f"continue_user_dialog_{question.uuid}",
                            ),
                            InlineKeyboardButton(
                                text="📸 Отправить фото",
                                callback_data=f"send_prescription_photo_{question.uuid}",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ Завершить консультацию",
                                callback_data=f"end_dialog_{question.uuid}",
                            )
                        ],
                    ]
                )

                # Отправляем только ответ фармацевта, без всей истории
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"💬 <b>Ответ фармацевта</b>\n\n"
                        f"{message.text}\n\n"
                        f"👨‍⚕️ <i>{pharmacist_info_text}</i>"
                    ),
                    parse_mode="HTML",
                    reply_markup=user_dialog_keyboard,
                )

                logger.info(f"Message sent to user {user.telegram_id}")

            except Exception as e:
                logger.error(
                    f"Failed to send message to user {user.telegram_id}: {e}",
                    exc_info=True,
                )

        # Фармацевту подтверждаем отправку кратко
        await message.answer(
            f"✅ <b>Ответ отправлен</b>\n\n"
            f"💬 {message.text[:100]}{'...' if len(message.text) > 100 else ''}",
            parse_mode="HTML",
            reply_markup=make_pharmacist_dialog_keyboard(question.uuid),
        )

        await state.set_state(QAStates.in_dialog_with_user)

    except Exception as e:
        logger.error(
            f"Error in handle_pharmacist_text_in_dialog for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке сообщения")
        await state.clear()


@router.message(QAStates.waiting_for_answer)
async def process_answer_text(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    is_pharmacist: bool,
    pharmacist: Pharmacist,
):
    """Обработка сообщения от фармацевта (ответ или уточнение)"""
    logger.info(f"Processing message from pharmacist {message.from_user.id}")

    if not is_pharmacist or not pharmacist:
        await message.answer("❌ Эта функция доступна только фармацевтам")
        await state.clear()
        return

    try:
        state_data = await state.get_data()
        question_uuid = state_data.get("question_uuid")

        if not question_uuid:
            await message.answer("❌ Не удалось найти вопрос для ответа")
            await state.clear()
            return

        result = await db.execute(
            select(Question).where(Question.uuid == question_uuid)
        )
        question = result.scalar_one_or_none()

        if not question:
            await message.answer("❌ Вопрос не найден")
            await state.clear()
            return

        if question.status == "completed":
            await message.answer("✅ Этот диалог уже завершен", show_alert=True)
            await state.clear()
            return

        if not pharmacist.is_online:
            pharmacist.is_online = True
            pharmacist.last_seen = get_utc_now_naive()
            await db.commit()

        answer = Answer(
            text=message.text,
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            created_at=get_utc_now_naive(),
        )
        db.add(answer)

        if question.status != "completed":
            question.status = "answered"
        question.answered_at = get_utc_now_naive()
        question.answered_by = pharmacist.uuid

        await DialogService.add_message(
            db=db,
            question_id=question.uuid,
            sender_type="pharmacist",
            sender_id=pharmacist.uuid,
            message_type="answer",
            text=message.text,
        )
        await db.commit()

        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            try:
                pharmacy_info = pharmacist.pharmacy_info or {}
                chain = pharmacy_info.get("chain", "Не указана")
                number = pharmacy_info.get("number", "Не указан")
                role = pharmacy_info.get("role", "Фармацевт")

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
                    " ".join(pharmacist_name_parts)
                    if pharmacist_name_parts
                    else "Фармацевт"
                )
                pharmacist_info_text = f"{pharmacist_name}"

                if chain and number:
                    pharmacist_info_text += f", {chain}, аптека №{number}"
                if role and role != "Фармацевт":
                    pharmacist_info_text += f" ({role})"

                user_dialog_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✍️ Ответить фармацевту",
                                callback_data=f"continue_user_dialog_{question.uuid}",
                            ),
                            InlineKeyboardButton(
                                text="📸 Отправить фото",
                                callback_data=f"send_prescription_photo_{question.uuid}",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ Завершить консультацию",
                                callback_data=f"end_dialog_{question.uuid}",
                            )
                        ],
                    ]
                )

                await DialogService.send_unified_dialog_history(
                    bot=message.bot,
                    chat_id=user.telegram_id,
                    question_uuid=question.uuid,
                    db=db,
                    title="ОТВЕТ ФАРМАЦЕВТА",
                    pre_text="💬 <b>ОТВЕТ ФАРМАЦЕВТА</b>\n\n",
                    post_text=f"\n\n👨‍⚕️ <b>Фармацевт:</b> {pharmacist_info_text}",
                    is_pharmacist=False,
                    show_buttons=True,
                    custom_buttons=user_dialog_keyboard.inline_keyboard,
                )

                logger.info(f"Full history sent to user {user.telegram_id}")

            except Exception as e:
                logger.error(
                    f"Failed to send history to user {user.telegram_id}: {e}",
                    exc_info=True,
                )

        await DialogService.send_unified_dialog_history(
            bot=message.bot,
            chat_id=message.chat.id,
            question_uuid=question.uuid,
            db=db,
            title="ВЫ ОТПРАВИЛИ ОТВЕТ",
            pre_text="💬 <b>ВЫ ОТПРАВИЛИ ОТВЕТ</b>\n\n",
            post_text="\n\n<b>Доступные действия:</b>",
            is_pharmacist=True,
            show_buttons=True,
            custom_buttons=make_pharmacist_dialog_keyboard(
                question.uuid
            ).inline_keyboard,
        )

        await state.set_state(QAStates.in_dialog_with_user)

    except Exception as e:
        logger.error(
            f"Error in process_answer_text for pharmacist {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("❌ Ошибка при отправке сообщения")
        await state.clear()
