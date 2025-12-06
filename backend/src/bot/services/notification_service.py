import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from bot.core import bot_manager
from db.qa_models import Pharmacist, User, Question
from bot.keyboards.qa_keyboard import make_question_keyboard
from bot.services.assignment_service import QuestionAssignmentService
from utils.time_utils import get_utc_now_naive
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


logger = logging.getLogger(__name__)

async def notify_pharmacists_about_new_question(question, db: AsyncSession):
    """Уведомление фармацевтов о новом вопросе"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            logger.error("Bot not initialized for notifications")
            return

        # Проверяем, нужно ли уведомлять всех
        if await QuestionAssignmentService.should_notify_all_pharmacists(question.uuid, db):
            # Уведомляем всех активных фармацевтов
            result = await db.execute(
                select(Pharmacist)
                .join(User, Pharmacist.user_id == User.uuid)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.is_active == True)
            )
            pharmacists = result.scalars().all()
        else:
            # Уведомляем только назначенного фармацевта
            taker = await QuestionAssignmentService.get_question_taker(question.uuid, db)
            pharmacists = [taker] if taker else []

        if not pharmacists:
            logger.info("No pharmacists to notify")
            return

        question_preview = question.text[:150] + "..." if len(question.text) > 150 else question.text

        for pharmacist in pharmacists:
            try:
                if pharmacist.user and pharmacist.user.telegram_id:
                    # Разные сообщения в зависимости от статуса
                    if pharmacist.is_online:
                        message_text = (
                            f"🔔 НОВЫЙ ВОПРОС!\n\n"
                            f"❓ Вопрос: {question_preview}\n\n"
                            f"💡 Статус: Вы в онлайн - можете ответить сразу!"
                        )
                        reply_markup = make_question_keyboard(question.uuid)
                    else:
                        message_text = (
                            f"📥 Новый вопрос ожидает ответа\n\n"
                            f"❓ Вопрос: {question_preview}\n\n"
                            f"💡 Статус: Вы в офлайн"
                        )
                        reply_markup = None

                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Notification sent to pharmacist {pharmacist.user.telegram_id}")

            except Exception as e:
                logger.error(f"Failed to notify pharmacist: {e}")

    except Exception as e:
        logger.error(f"Error in notify_pharmacists_about_new_question: {e}")

# bot/services/notification_service.py - исправленная функция notify_about_clarification
# Замените функцию notify_about_clarification на эту:

async def notify_about_clarification(
    original_question: Question,
    clarification_text: str,
    db: AsyncSession
):
    """Уведомление об уточнении - АДАПТИРОВАННАЯ ВЕРСИЯ"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            logger.error("Bot not initialized for notifications")
            return

        # Получаем фармацевта, который взял исходный вопрос
        from bot.services.assignment_service import QuestionAssignmentService
        taker = await QuestionAssignmentService.get_question_taker(
            str(original_question.uuid),
            db
        )

        pharmacists_to_notify = []

        if not taker:
            # Если никто не взял вопрос, уведомляем всех онлайн фармацевтов
            result = await db.execute(
                select(Pharmacist)
                .join(User, Pharmacist.user_id == User.uuid)
                .options(selectinload(Pharmacist.user))
                .where(
                    Pharmacist.is_active == True,
                    Pharmacist.is_online == True
                )
            )
            pharmacists_to_notify = result.scalars().all()
        else:
            # Уведомляем только фармацевта, который взял вопрос
            taker_result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.uuid == taker.uuid)
            )
            taker_with_user = taker_result.scalar_one_or_none()
            if taker_with_user:
                pharmacists_to_notify = [taker_with_user]

        for pharmacist in pharmacists_to_notify:
            if pharmacist.user and pharmacist.user.telegram_id:
                message_text = (
                    f"🔍 УТОЧНЕНИЕ К ВОПРОСУ!\n\n"
                    f"❓ Исходный вопрос: {original_question.text[:200]}...\n\n"
                    f"💬 Уточнение пользователя: {clarification_text[:200]}...\n\n"
                )

                if pharmacist.is_online:
                    message_text += "💡 Статус: Вы в онлайн - можете ответить сразу!"
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="💬 Ответить на уточнение",
                                    callback_data=f"answer_{original_question.uuid}"  # Ответ на исходный вопрос
                                )
                            ]
                        ]
                    )
                else:
                    message_text += "💡 Статус: Вы в офлайн"
                    reply_markup = None

                await bot.send_message(
                    chat_id=pharmacist.user.telegram_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
                logger.info(f"Clarification notification sent to pharmacist {pharmacist.user.telegram_id}")

    except Exception as e:
        logger.error(f"Error in notify_about_clarification: {e}", exc_info=True)

async def get_online_pharmacists(db: AsyncSession):
    """Получить список онлайн фармацевтов"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(
                and_(
                    Pharmacist.is_online == True,
                    Pharmacist.is_active == True,
                )
            )
        )
        pharmacists = result.scalars().all()
        logger.info(f"Found {len(pharmacists)} online pharmacists")
        return pharmacists
    except Exception as e:
        logger.error(f"Error getting online pharmacists: {e}")
        return []

