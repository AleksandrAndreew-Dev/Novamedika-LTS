
from bot.core import bot_manager
from sqlalchemy import select, and_
from datetime import timedelta
from utils.time_utils import get_utc_now_naive
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from db.qa_models import Pharmacist, User
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

async def notify_pharmacists_about_new_question(question, db: AsyncSession):
    """Уведомление фармацевтов о новом вопросе - РАСШИРЕННАЯ ВЕРСИЯ"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            logger.error("Bot not initialized for notifications")
            return

        # Получаем ВСЕХ активных фармацевтов (не только онлайн)
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.is_active == True)
        )
        all_pharmacists = result.scalars().all()

        logger.info(f"Found {len(all_pharmacists)} active pharmacists to notify")

        if not all_pharmacists:
            logger.info("No active pharmacists to notify")
            return

        question_preview = question.text[:150] + "..." if len(question.text) > 150 else question.text

        from bot.keyboards.qa_keyboard import make_question_keyboard

        notified_count = 0
        online_notified = 0
        offline_notified = 0

        for pharmacist in all_pharmacists:
            try:
                if pharmacist.user and pharmacist.user.telegram_id:
                    # Разные сообщения для онлайн и офлайн фармацевтов
                    if pharmacist.is_online:
                        message_text = (
                            f"🔔 НОВЫЙ ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ!\n\n"
                            f"❓ Вопрос: {question_preview}\n\n"
                            f"💡 Статус: Вы в онлайн - можете ответить сразу!\n"
                            f"Используйте /questions чтобы просмотреть вопрос"
                        )
                        online_notified += 1
                    else:
                        message_text = (
                            f"📥 Новый вопрос ожидает ответа\n\n"
                            f"❓ Вопрос: {question_preview}\n\n"
                            f"💡 Статус: Вы в офлайн - перейдите в онлайн чтобы ответить\n"
                            f"Используйте /online чтобы начать принимать вопросы"
                        )
                        offline_notified += 1

                    await bot.send_message(
                        chat_id=pharmacist.user.telegram_id,
                        text=message_text,
                        reply_markup=make_question_keyboard(question.uuid) if pharmacist.is_online else None
                    )
                    notified_count += 1
                    logger.info(f"Notification sent to pharmacist {pharmacist.user.telegram_id}")

                    # Небольшая задержка между отправками
                    import asyncio
                    await asyncio.sleep(0.1)

            except Exception as e:
                pharmacist_id = pharmacist.user.telegram_id if pharmacist.user else "unknown"
                logger.error(f"Failed to notify pharmacist {pharmacist_id}: {e}")

        logger.info(f"Notified {notified_count} pharmacists about new question {question.uuid} "
                   f"(online: {online_notified}, offline: {offline_notified})")

    except Exception as e:
        logger.error(f"Error in notify_pharmacists_about_new_question: {e}", exc_info=True)

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
