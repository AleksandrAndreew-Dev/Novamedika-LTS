import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core import bot_manager
from bot.handlers.clarify_handlers import router as clarify_router
from bot.handlers import (
    common_router,
    registration_router,
    user_questions_router,
    qa_handlers_router,
    dialog_management_router,
)
from bot.middleware.role_middleware import RoleMiddleware
from db.database import async_session_maker
from bot.middleware.db import DbMiddleware

from routers import booking_orders
from routers import pharmacy_api

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Инициализация rate limiter
limiter = Limiter(key_func=get_remote_address)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Главное меню"),
        BotCommand(command="/ask", description="Задать вопрос"),
        BotCommand(command="/my_questions", description="Мои вопросы"),
        BotCommand(command="/help", description="Помощь"),
        BotCommand(command="/online", description="Войти в онлайн (фармацевт)"),
        BotCommand(command="/offline", description="Выйти из онлайн (фармацевт)"),
        BotCommand(
            command="/questions", description="Вопросы пользователей (фармацевт)"
        ),
    ]
    await bot.set_my_commands(commands)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Проверка обязательных переменных окружения
    required_env_vars = ["SECRET_KEY", "DATABASE_URL"]
    missing = [v for v in required_env_vars if not os.getenv(v)]
    if missing:
        logger.critical(f"MISSING required env vars: {missing}")
        raise RuntimeError(f"Missing required env vars: {missing}")

    # Alembic миграции применяются через entrypoint.sh — не нужно create_all()
    logger.info("Database migrations handled by Alembic (entrypoint.sh)")

    # Предупреждение если REGISTRATION_SECRET_WORD не установлен
    if not os.getenv("REGISTRATION_SECRET_WORD"):
        logger.warning(
            "REGISTRATION_SECRET_WORD is NOT SET — pharmacist registration will be blocked"
        )

    # Инициализация бота (не критична для API — продолжаем без бота)
    bot, dp = await bot_manager.initialize()

    if bot and dp:
        logger.info("Bot initialized successfully")
        dp.update.outer_middleware(DbMiddleware())
        dp.update.outer_middleware(RoleMiddleware())

        # Порядок роутеров важен: специфичные handlers ДО общих (unknown_command)
        dp.include_router(registration_router)
        dp.include_router(qa_handlers_router)
        dp.include_router(dialog_management_router)
        dp.include_router(user_questions_router)
        dp.include_router(clarify_router)
        dp.include_router(common_router)

        # УСТАНОВКА КОМАНД БОТА
        try:
            await set_bot_commands(bot)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")

        # УСТАНОВКА WEBHOOK ПРИ ЗАПУСКЕ
        # Проверяем текущий webhook, чтобы не вызывать flood control
        try:
            webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
            secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")

            if webhook_url:
                # Проверяем, установлен ли уже нужный webhook
                current_info = await bot.get_webhook_info()
                current_url = current_info.url if hasattr(current_info, "url") else None

                if current_url != webhook_url:
                    webhook_config = {
                        "url": webhook_url,
                        "drop_pending_updates": True,
                        "max_connections": 40,
                    }

                    if secret_token:
                        webhook_config["secret_token"] = secret_token

                    await bot.set_webhook(**webhook_config)
                    logger.info(f"Webhook set successfully: {webhook_url}")
                else:
                    logger.info(f"Webhook already set, skipping: {webhook_url}")
            else:
                logger.warning(
                    "TELEGRAM_WEBHOOK_URL not set — bot will not receive updates"
                )

        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")

        logger.info("Bot started successfully with webhook")
    else:
        logger.warning(
            "Bot NOT initialized — API will work, but Telegram features are disabled"
        )

    yield

    # Завершение работы бота
    if bot:
        await bot_manager.shutdown()

        # УДАЛЕНИЕ WEBHOOK ПРИ ЗАВЕРШЕНИИ
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted on shutdown")
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")


app = FastAPI(lifespan=lifespan, title="Novamedika Q&A Bot API")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Слишком много запросов. Попробуйте позже."},
    )


# ДОБАВИТЬ CORS MIDDLEWARE
origins = os.getenv("CORS_ORIGINS", "").split(",")
if not origins or origins == [""]:
    origins = [
        "http://localhost:3000",
        "https://spravka.novamedika.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров
from routers import (
    pharmacist_auth,
    qa,
    telegram_bot,
    search,
    upload,
    pharmacies_info,
)

app.include_router(pharmacist_auth.router, tags=["auth"])
app.include_router(qa.router, tags=["qa"])
app.include_router(telegram_bot.router, tags=["bot"])
app.include_router(search.router, tags=["search"])
app.include_router(upload.router, tags=["upload"])
app.include_router(pharmacies_info.router, tags=["pharmacies"])
app.include_router(booking_orders.router, tags=["booking"])
app.include_router(pharmacy_api.router, tags=["pharmacy-api"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "Novamedika Q&A Bot API"}


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check(request: Request):
    if request.method == "HEAD":
        return JSONResponse(content={"status": "healthy"})
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
