from fastapi import APIRouter, Request, HTTPException
from aiogram.types import Update
import logging
import os
import json

from bot.core import bot_manager


from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func


from db.database import get_db
from db.qa_models import User, Question, Pharmacist, Answer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/")
async def telegram_webhook(request: Request):
    """Webhook endpoint для Telegram бота"""
    try:
        # Проверяем секретный токен для безопасности
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if secret_token:
            received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if received_secret != secret_token:
                logger.warning(
                    f"Invalid secret token. Received: {received_secret}, Expected: {secret_token}"
                )
                return {"status": "error", "detail": "Unauthorized"}

        bot, dp = await bot_manager.initialize()
        if not bot or not dp:
            raise HTTPException(status_code=500, detail="Bot not configured")

        # Получаем обновление от Telegram
        try:
            update_data = await request.json()
        except json.JSONDecodeError as e:
            body = await request.body()
            logger.error(f"Invalid JSON received: {body}")
            return {"status": "error", "detail": "Invalid JSON format"}

        update = Update(**update_data)

        # Обрабатываем обновление через диспетчер
        await dp.feed_webhook_update(bot=bot, update=update)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error", "detail": str(e)}


@router.post("/set_webhook/")
async def set_webhook():
    """Установка вебхука (вызывается при деплое)"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            return {"status": "error", "detail": "Bot not configured"}

        # Проверяем, что бот доступен
        try:
            bot_info = await bot.get_me()
            logger.info(f"Bot authorized as: @{bot_info.username}")
        except Exception as e:
            return {"status": "error", "detail": f"Bot authorization failed: {str(e)}"}

        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        if not webhook_url:
            return {"status": "error", "detail": "TELEGRAM_WEBHOOK_URL not set"}

        # Устанавливаем webhook с секретным токеном для безопасности
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        webhook_config = {
            "url": webhook_url,
            "drop_pending_updates": True,
            "max_connections": 40,
        }

        if secret_token:
            webhook_config["secret_token"] = secret_token

        result = await bot.set_webhook(**webhook_config)
        webhook_info = await bot.get_webhook_info()

        logger.info(f"Webhook set successfully: {webhook_url}")
        logger.info(f"Webhook info: {webhook_info}")

        return {
            "status": "success",
            "message": "Webhook set successfully",
            "bot_info": {
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "id": bot_info.id,
            },
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "ip_address": webhook_info.ip_address,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates,
            },
        }

    except Exception as e:
        logger.error(f"Set webhook error: {str(e)}")
        return {"status": "error", "detail": str(e)}


@router.post("/delete_webhook/")
async def delete_webhook():
    """Удаление вебхука (для debugging)"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            return {"status": "error", "detail": "Bot not configured"}

        result = await bot.delete_webhook(drop_pending_updates=True)
        return {"status": "success", "message": "Webhook deleted", "result": result}

    except Exception as e:
        logger.error(f"Delete webhook error: {str(e)}")
        return {"status": "error", "detail": str(e)}


@router.get("/webhook_info/")
async def get_webhook_info():
    """Получить информацию о вебхуке"""
    try:
        bot, _ = await bot_manager.initialize()
        if not bot:
            return {"status": "error", "detail": "Bot not configured"}

        webhook_info = await bot.get_webhook_info()

        return {
            "status": "success",
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "ip_address": webhook_info.ip_address,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates,
            },
        }

    except Exception as e:
        logger.error(f"Get webhook info error: {str(e)}")
        return {"status": "error", "detail": str(e)}

from dotenv import load_dotenv
from fastapi import Header

load_dotenv(".env")

ADMIN_API_KEYS = [k.strip() for k in os.getenv("ADMIN_API_KEYS", "").split(",") if k.strip()]

async def verify_admin_api_key(x_api_key: str | None = Header(None)):
    """Проверка API ключа админа. Ожидает заголовок X-Api-Key"""
    if not ADMIN_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API keys not configured",
        )

    if not x_api_key or x_api_key not in ADMIN_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
    return True



@router.post("/qa/drop", summary="Очистка всей базы QA")
async def drop_qa_database(
    admin: bool = Depends(verify_admin_api_key), db: AsyncSession = Depends(get_db)
):
    """Очистка всей базы QA (только для админов)"""
    try:
        # Отключаем внешние ключи (для PostgreSQL)
        await db.execute(text("SET session_replication_role = 'replica';"))

        # Очищаем таблицы в правильном порядке (с учетом foreign keys)
        tables = ["qa_answers", "qa_questions", "qa_pharmacists", "qa_users"]

        cleared_tables = []
        for table in tables:
            await db.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
            cleared_tables.append(table)
            logger.info(f"Cleared table: {table}")

        # Включаем обратно внешние ключи
        await db.execute(text("SET session_replication_role = 'origin';"))
        await db.commit()

        return {
            "status": "success",
            "message": "QA database cleared successfully",
            "cleared_tables": cleared_tables,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error dropping QA database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing database: {str(e)}",
        )


@router.get("/qa/stats", summary="Статистика базы QA")
async def get_qa_stats(
    admin: bool = Depends(verify_admin_api_key), db: AsyncSession = Depends(get_db)
):
    """Получить статистику базы QA"""
    try:
        # Считаем количество записей в каждой таблице
        user_count = await db.execute(select(func.count(User.uuid)))
        pharmacist_count = await db.execute(select(func.count(Pharmacist.uuid)))
        question_count = await db.execute(select(func.count(Question.uuid)))
        answer_count = await db.execute(select(func.count(Answer.uuid)))

        # Вопросы по статусам
        pending_questions = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "pending")
        )
        answered_questions = await db.execute(
            select(func.count(Question.uuid)).where(Question.status == "answered")
        )

        # Активные фармацевты
        active_pharmacists = await db.execute(
            select(func.count(Pharmacist.uuid)).where(Pharmacist.is_active == True)
        )

        # Онлайн фармацевты (активные за последние 5 минут)
        from utils.time_utils import get_utc_now_naive
        from datetime import timedelta

        online_threshold = get_utc_now_naive() - timedelta(minutes=5)
        online_pharmacists = await db.execute(
            select(func.count(Pharmacist.uuid))
            .where(Pharmacist.is_active == True)
            .where(Pharmacist.is_online == True)
            .where(Pharmacist.last_seen >= online_threshold)
        )

        stats = {
            "users": user_count.scalar(),
            "pharmacists": {
                "total": pharmacist_count.scalar(),
                "active": active_pharmacists.scalar(),
                "online": online_pharmacists.scalar(),
            },
            "questions": {
                "total": question_count.scalar(),
                "pending": pending_questions.scalar(),
                "answered": answered_questions.scalar(),
                "answer_rate": (
                    answered_questions.scalar() / question_count.scalar()
                    if question_count.scalar() > 0
                    else 0
                ),
            },
            "answers": answer_count.scalar(),
        }

        return {
            "status": "success",
            "stats": stats,
            "timestamp": get_utc_now_naive().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting QA stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting statistics: {str(e)}",
        )


@router.post("/qa/reset-pharmacists-status", summary="Сброс статуса фармацевтов")
async def reset_pharmacists_status(
    admin: bool = Depends(verify_admin_api_key), db: AsyncSession = Depends(get_db)
):
    """Сбросить всех фармацевтов в офлайн статус"""
    try:
        result = await db.execute(
            select(Pharmacist).where(Pharmacist.is_online == True)
        )
        online_pharmacists = result.scalars().all()

        for pharmacist in online_pharmacists:
            pharmacist.is_online = False

        await db.commit()

        return {
            "status": "success",
            "message": f"Reset {len(online_pharmacists)} pharmacists to offline",
            "reset_count": len(online_pharmacists),
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error resetting pharmacists status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting pharmacists status: {str(e)}",
        )


@router.get("/qa/questions/pending", summary="Список ожидающих вопросов")
async def get_pending_questions(
    admin: bool = Depends(verify_admin_api_key), db: AsyncSession = Depends(get_db)
):
    """Получить список всех ожидающих вопросов"""
    try:
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Question)
            .options(selectinload(Question.user), selectinload(Question.answers))
            .where(Question.status == "pending")
            .order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()

        questions_data = []
        for question in questions:
            questions_data.append(
                {
                    "id": str(question.uuid),
                    "text": question.text,
                    "created_at": question.created_at.isoformat(),
                    "user": {
                        "telegram_id": question.user.telegram_id,
                        "first_name": question.user.first_name,
                        "username": question.user.telegram_username,
                    },
                    "answer_count": len(question.answers),
                }
            )

        return {
            "status": "success",
            "count": len(questions_data),
            "questions": questions_data,
        }

    except Exception as e:
        logger.error(f"Error getting pending questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pending questions: {str(e)}",
        )
