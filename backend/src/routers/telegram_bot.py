from fastapi import APIRouter, Request, HTTPException, Depends
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
from services.user_service import get_or_create_user
from auth.session_manager import (
    clear_all_pharmacist_sessions,
    get_session,
    recreate_session_from_data,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ConsentCheckRequest(BaseModel):
    """Запрос на проверку согласия пользователя из Telegram WebApp"""

    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class ConsentCheckResponse(BaseModel):
    """Ответ с статусом согласия пользователя"""

    has_consent: bool
    consent_privacy_policy: bool | None = None
    needs_webapp_consent: bool


@router.post("/webhook/")
async def telegram_webhook(request: Request):
    """Webhook endpoint для Telegram бота"""
    try:
        # Проверка секретного токена
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if secret_token:
            received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if received_secret != secret_token:
                logger.warning("Invalid secret token")
                return {"status": "error", "detail": "Unauthorized"}

        # ✅ Используем уже инициализированные bot и dp
        bot = bot_manager.get_bot()
        dp = bot_manager.get_dp()

        # Авто-реинициализация после /qa/drop (если bot/dp были сброшены)
        if not bot or not dp:
            logger.warning(
                "Bot or dispatcher not initialized, attempting auto-reinitialization..."
            )
            bot, dp = await bot_manager.initialize()
            if not bot or not dp:
                logger.error("Bot auto-reinitialization failed")
                raise HTTPException(status_code=503, detail="Bot service not ready")
            logger.info("✅ Bot auto-reinitialized successfully")

        # Получение JSON
        try:
            update_data = await request.json()
        except json.JSONDecodeError as e:
            body = await request.body()
            logger.error(f"Invalid JSON received: {body}")
            return {"status": "error", "detail": "Invalid JSON format"}

        update = Update(**update_data)

        # Логирование типа обновления (улучшенная версия)
        if update.message:
            logger.info(
                f"📨 Webhook: Message from user {update.message.from_user.id}: '{update.message.text[:50] if update.message.text else 'NO TEXT'}'"
            )
        elif update.callback_query:
            logger.info(
                f"📨 Webhook: Callback from user {update.callback_query.from_user.id}: '{update.callback_query.data}'"
            )
        elif update.edited_message:
            logger.info(
                f"📨 Webhook: Edited message from user {update.edited_message.from_user.id}"
            )
        else:
            logger.info(
                f"📨 Webhook: Update id={update.update_id}, type={update.event_type}"
            )

        # Обработка обновления
        try:
            result = await dp.feed_update(bot, update)
            # В aiogram 3.x feed_update возвращает None по умолчанию,
            # даже когда обработчик успешно выполнился (если handler не возвращает значение явно)
            # Поэтому мы не можем полагаться на return value для определения успешности обработки
            # aiogram сам логирует успешную обработку через "Update id=X is handled"
            logger.debug(f"Update {update.update_id} processed, result={result}")

        except Exception as e:
            logger.error(
                f"❌ Error processing update {update.update_id}: {e}", exc_info=True
            )
            raise

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
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

from fastapi import Header, HTTPException, status


# Admin API Keys для критичных операций
# Читаются при каждом запросе для поддержки hot-reload без перезапуска
def get_admin_api_keys():
    """Получить список ADMIN API Keys из окружения"""
    keys_str = os.getenv("ADMIN_API_KEYS", "")
    return [k.strip() for k in keys_str.split(",") if k.strip()]


async def verify_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    admin_keys = get_admin_api_keys()

    if not admin_keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API keys not configured",
        )
    if x_api_key not in admin_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key"
        )
    return True


@router.post("/qa/drop", summary="Очистка всей базы QA")
async def drop_qa_database(
    request: Request,
    admin: bool = Depends(verify_admin_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Очистка всей базы QA (только для админов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(f"⚠️ /qa/drop invoked from IP {client_ip}")

    try:
        preserved_session_token = None
        preserved_session_data = None
        auth_header = request.headers.get("authorization")
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                preserved_session_token = auth_header.split(" ", 1)[1].strip()
            else:
                preserved_session_token = auth_header.strip()

        if preserved_session_token:
            preserved_session_data = await get_session(preserved_session_token)
            if preserved_session_data:
                logger.info(
                    "Preserving current pharmacist session after /qa/drop: %s",
                    preserved_session_token[:10],
                )

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

        logger.warning(
            f"⚠️ /qa/drop completed — client: {client_ip}, "
            f"tables: {cleared_tables}. "
            f"Bot auto-restart scheduled."
        )

        # Clear all stale Redis sessions pointing to deleted pharmacist records
        await clear_all_pharmacist_sessions()

        # Preserve current session if available and re-create it after cleanup
        new_session_token = None
        if preserved_session_data:
            new_session_token = await recreate_session_from_data(preserved_session_data)
            if new_session_token:
                logger.info("Recreated pharmacist session after /qa/drop")

        # Auto-restart: сброс bot_manager (FSM storage, bot session, dispatcher)
        await bot_manager.reset_with_retry()

        return {
            "status": "success",
            "message": "QA database cleared successfully",
            "cleared_tables": cleared_tables,
            "client_ip": client_ip,
            "preserved_session": bool(new_session_token),
            "session_token": new_session_token,
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
            "questions": questions_data,
            "total": len(questions_data),
        }

    except Exception as e:
        logger.error(f"Error getting pending questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pending questions: {str(e)}",
        )


@router.post("/webapp/check-consent", response_model=ConsentCheckResponse)
async def check_webapp_consent(
    request: ConsentCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Проверка статуса согласия пользователя при открытии WebApp из Telegram бота.

    Этот endpoint вызывается фронтендом при инициализации Telegram WebApp
    для определения, нужно ли показывать модальное окно с запросом согласия
    на обработку данных в контексте WebApp (поиск лекарств, бронирование).

    Логика:
    1. Если пользователь дал согласие в боте (consent_privacy_policy = True) -
       считаем что согласие есть для базовых функций
    2. Но для WebApp с дополнительными функциями (бронирование с передачей телефона аптеке)
       может потребоваться отдельное подтверждение

    Args:
        telegram_id: Telegram ID пользователя из initData
        first_name, last_name, username: Дополнительные данные пользователя

    Returns:
        has_consent: Есть ли базовое согласие
        consent_privacy_policy: Статус согласия из БД
        needs_webapp_consent: Нужно ли дополнительное согласие для WebApp
    """
    try:
        # Получаем или создаем пользователя
        user = await get_or_create_user(
            db=db,
            telegram_id=request.telegram_id,
            first_name=request.first_name,
            last_name=request.last_name,
            telegram_username=request.username,
        )

        # Проверяем статус согласия
        has_basic_consent = (
            user.consent_privacy_policy
            if hasattr(user, "consent_privacy_policy")
            else False
        )

        # Для WebApp с функцией бронирования требуется явное согласие
        # даже если есть базовое согласие из бота
        # Это связано с тем, что в WebApp обрабатываются дополнительные данные
        # (телефон для передачи аптеке)
        needs_additional_consent = not has_basic_consent

        logger.info(
            f"WebApp consent check for telegram_id={request.telegram_id}: "
            f"has_consent={has_basic_consent}, needs_additional={needs_additional_consent}"
        )

        return ConsentCheckResponse(
            has_consent=has_basic_consent,
            consent_privacy_policy=(
                user.consent_privacy_policy
                if hasattr(user, "consent_privacy_policy")
                else None
            ),
            needs_webapp_consent=needs_additional_consent,
        )

    except Exception as e:
        logger.error(f"Error checking WebApp consent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check consent status",
        )
