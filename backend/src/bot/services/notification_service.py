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
    """Более умные уведомления"""
    online_pharmacists = await get_online_pharmacists(db)

    if not online_pharmacists:
        return

    question_preview = question.text[:150] + "..." if len(question.text) > 150 else question.text

    for pharmacist in online_pharmacists:
        try:
            await message.bot.send_message(
                chat_id=pharmacist.user.telegram_id,
                text=f"❓ Новый вопрос:\n\n{question_preview}",
                reply_markup=make_question_keyboard(question.uuid)
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления: {e}")
