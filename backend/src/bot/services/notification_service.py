from bot.core import bot_manager
from sqlalchemy import select
from datetime import timedelta
from utils.time_utils import get_utc_now_naive

import logging
from sqlalchemy.ext.asyncio import AsyncSession


from db.qa_models import Pharmacist, User

import asyncio

logger = logging.getLogger(__name__)


async def notify_pharmacists_about_new_question(question, db: AsyncSession):
    """Уведомить всех активных фармацевтов о новом вопросе"""
    try:
        bot, _ = await bot_manager.initialize()  # ✅ Правильная инициализация
        if not bot:
            logger.error("Bot not available for notifications")
            return

        online_threshold = get_utc_now_naive() - timedelta(minutes=5)

        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(Pharmacist.is_active == True)
            .where(Pharmacist.is_online == True)
            .where(Pharmacist.last_seen >= online_threshold)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            logger.info("No online pharmacists found for notification")
            return

        message_text = (
            "🆕 Новый вопрос от пользователя!\n\n"
            f"❓ Вопрос: {question.text[:200]}{'...' if len(question.text) > 200 else ''}\n"
            f"📅 Время: {question.created_at.strftime('%H:%M %d.%m.%Y')}\n\n"
            "Для ответа используйте команду /questions"
        )

        for pharmacist in pharmacists:
            try:
                if pharmacist.user and pharmacist.user.telegram_id:
                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text
                    )
                    logger.info(f"Notified pharmacist {pharmacist.uuid}")
            except Exception as e:
                logger.error(f"Failed to notify pharmacist {pharmacist.uuid}: {e}")

    except Exception as e:
        logger.error(f"Error in notification service: {e}")
