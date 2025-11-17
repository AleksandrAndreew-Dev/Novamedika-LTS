# notification_service.py - ИСПРАВЛЕННЫЙ
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.qa_models import Pharmacist, User
from bot.core import bot_manager

logger = logging.getLogger(__name__)

async def notify_pharmacists_about_new_question(question, db: AsyncSession):
    """Уведомить всех активных фармацевтов о новом вопросе"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            return

        # Получаем всех активных фармацевтов
        result = await db.execute(
            select(Pharmacist)
            .join(Pharmacist.user)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        message_text = (
            "🆕 Новый вопрос от пользователя!\n\n"
            f"❓ Вопрос: {question.text[:200]}...\n"
            f"📅 Время: {question.created_at.strftime('%H:%M %d.%m.%Y')}\n\n"
            "Для ответа используйте команду /questions"
        )

        for pharmacist in pharmacists:
            try:
                if pharmacist.user.telegram_id:
                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text
                    )
            except Exception as e:
                logger.error(f"Failed to notify pharmacist {pharmacist.uuid}: {e}")

    except Exception as e:
        logger.error(f"Error in notification service: {e}")
