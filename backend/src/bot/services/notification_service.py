
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from db.qa_models import Pharmacist, User
from bot.core import bot_manager
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

async def notify_pharmacists_about_new_question(question, db: AsyncSession):
    """Уведомить всех активных фармацевтов о новом вопросе"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            return

        # Используем правильные названия колонок
        online_threshold = get_utc_now_naive() - timedelta(minutes=5)
        result = await db.execute(
            select(Pharmacist)
            .join(Pharmacist.user)
            .where(Pharmacist.is_active == True)
            .where(Pharmacist.is_online == True)  # Теперь колонка существует
            .where(Pharmacist.last_seen >= online_threshold)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            logger.info("No online pharmacists to notify")
            return

        message_text = (
            "🆕 Новый вопрос от пользователя!\n\n"
            f"❓ Вопрос: {question.text[:200]}...\n"
            f"📅 Время: {question.created_at.strftime('%H:%M %d.%m.%Y')}\n\n"
            "Для ответа используйте команду /questions"
        )

        notified_count = 0
        for pharmacist in pharmacists:
            try:
                if pharmacist.user.telegram_id:
                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text
                    )
                    notified_count += 1
            except Exception as e:
                logger.error(f"Failed to notify pharmacist {pharmacist.uuid}: {e}")

        logger.info(f"Notified {notified_count} online pharmacists about new question")

    except Exception as e:
        logger.error(f"Error in notification service: {e}")
