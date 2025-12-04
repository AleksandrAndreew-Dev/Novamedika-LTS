
from bot.core import bot_manager
from sqlalchemy import select, and_
from datetime import timedelta
from utils.time_utils import get_utc_now_naive
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from db.qa_models import Pharmacist, User
from bot.keyboards.qa_keyboard import make_question_keyboard, make_clarification_keyboard
from sqlalchemy.orm import selectinload
from bot.services.assignment_service import QuestionAssignmentService


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
                .where(Pharmacist.is_active == True)
            )
            pharmacists = result.scalars().all()

            # Загружаем user для каждого фармацевта
            for pharmacist in pharmacists:
                await db.refresh(pharmacist, attribute_names=['user'])
        else:
            # Уведомляем только назначенного фармацевта
            taker = await QuestionAssignmentService.get_question_taker(question.uuid, db)
            pharmacists = [taker] if taker else []
            if taker:
                await db.refresh(taker, attribute_names=['user'])

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

async def notify_about_clarification(question, original_question, db: AsyncSession):
    """Уведомление об уточнении"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            logger.error("Bot not initialized for notifications")
            return

        # Получаем фармацевта, который взял исходный вопрос
        taker = await QuestionAssignmentService.get_question_taker(
            original_question.uuid,
            db
        )

        if not taker:
            # Если никто не взял вопрос, уведомляем всех онлайн фармацевтов
            result = await db.execute(
                select(Pharmacist)
                .where(
                    and_(
                        Pharmacist.is_active == True,
                        Pharmacist.is_online == True
                    )
                )
            )
            pharmacists = result.scalars().all()

            # Загружаем user для каждого фармацевта отдельным запросом
            for pharmacist in pharmacists:
                await db.refresh(pharmacist, attribute_names=['user'])
        else:
            # Уведомляем только фармацевта, который взял вопрос
            pharmacists = [taker]
            # Загружаем user для taker
            await db.refresh(taker, attribute_names=['user'])

        for pharmacist in pharmacists:
            try:
                if pharmacist.user and pharmacist.user.telegram_id:
                    message_text = (
                        f"🔍 УТОЧНЕНИЕ К ВОПРОСУ!\n\n"
                        f"❓ Исходный вопрос: {original_question.text}\n\n"
                        f"💬 Уточнение: {question.text}\n\n"
                    )

                    if pharmacist.is_online:
                        message_text += "💡 Статус: Вы в онлайн - можете ответить сразу!"
                        reply_markup = make_clarification_keyboard(question.uuid)
                    else:
                        message_text += "💡 Статус: Вы в офлайн"
                        reply_markup = None

                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text,
                        reply_markup=reply_markup
                    )

            except Exception as e:
                logger.error(f"Failed to notify pharmacist about clarification: {e}")

    except Exception as e:
        logger.error(f"Error in notify_about_clarification: {e}")

async def get_online_pharmacists(db: AsyncSession):
    """Получить список онлайн фармацевтов"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .where(
                and_(
                    Pharmacist.is_online == True,
                    Pharmacist.is_active == True,
                )
            )
        )
        pharmacists = result.scalars().all()

        # Загружаем user для каждого фармацевта
        for pharmacist in pharmacists:
            await db.refresh(pharmacist, attribute_names=['user'])

        logger.info(f"Found {len(pharmacists)} online pharmacists")
        return pharmacists
    except Exception as e:
        logger.error(f"Error getting online pharmacists: {e}")
        return []

