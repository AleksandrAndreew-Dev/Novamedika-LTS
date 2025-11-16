from fastapi import APIRouter, Request, HTTPException
from aiogram.types import Update
import logging
import os
import json

from bot.core import bot_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])

@router.post("/webhook/")
async def telegram_webhook(request: Request):
    """Webhook endpoint для Telegram бота"""
    try:
        # Проверяем секретный токен для безопасности
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if secret_token:
            received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if received_secret != secret_token:
                logger.warning(f"Invalid secret token. Received: {received_secret}, Expected: {secret_token}")
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
                "id": bot_info.id
            },
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "ip_address": webhook_info.ip_address,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates
            }
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
                "allowed_updates": webhook_info.allowed_updates
            }
        }

    except Exception as e:
        logger.error(f"Get webhook info error: {str(e)}")
        return {"status": "error", "detail": str(e)}
