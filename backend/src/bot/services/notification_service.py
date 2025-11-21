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
    """Уведомление фармацевтов о новом вопросе"""
    try:
        # Получаем бота
        bot, _ = await bot_manager.initialize()
        if not bot:
            logger.error("Bot not initialized for notifications")
            return

        # Получаем онлайн фармацевтов с подгрузкой пользователя
        five_minutes_ago = get_utc_now_naive() - timedelta(minutes=5)

        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(
                Pharmacist.is_online == True,
                Pharmacist.is_active == True,
                Pharmacist.last_seen >= five_minutes_ago
            )
        )
        online_pharmacists = result.scalars().all()

        logger.info(f"Found {len(online_pharmacists)} online pharmacists to notify")

        if not online_pharmacists:
            logger.info("No online pharmacists to notify")
            return

        question_preview = question.text[:150] + "..." if len(question.text) > 150 else question.text

        from bot.keyboards.qa_keyboard import make_question_keyboard

        notified_count = 0
        for pharmacist in online_pharmacists:
            try:
                if pharmacist.user and pharmacist.user.telegram_id:
                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=f"🔔 Новый вопрос от пользователя!\n\n"
                             f"❓ Вопрос: {question_preview}\n\n"
                             f"Используйте /questions чтобы ответить",
                        reply_markup=make_question_keyboard(question.uuid)
                    )
                    notified_count += 1
                    logger.info(f"Notification sent to pharmacist {pharmacist.user.telegram_id}")
            except Exception as e:
                pharmacist_id = pharmacist.user.telegram_id if pharmacist.user else "unknown"
                logger.error(f"Failed to notify pharmacist {pharmacist_id}: {e}")

        logger.info(f"Notified {notified_count} pharmacists about new question {question.uuid}")

    except Exception as e:
        logger.error(f"Error in notify_pharmacists_about_new_question: {e}", exc_info=True)


async def get_online_pharmacists(db: AsyncSession):
    """Получить список онлайн фармацевтов"""
    try:
        five_minutes_ago = get_utc_now_naive() - timedelta(minutes=5)
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .where(
                Pharmacist.is_online == True,
                Pharmacist.is_active == True,
                Pharmacist.last_seen >= five_minutes_ago
            )
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting online pharmacists: {e}")
        return []
