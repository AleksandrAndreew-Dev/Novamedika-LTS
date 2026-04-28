import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

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
from db.database import async_session_maker, init_models
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

    # Alembic миграции применяются через entrypoint.sh
    # Fallback: если миграции ещё не применялись — create_all как страховка
    try:
        await init_models()
        logger.info("Database tables ensured (fallback via create_all)")
    except Exception as e:
        logger.warning(f"create_all failed (may be normal if alembic already ran): {e}")

    # Предупреждение если REGISTRATION_SECRET_WORD не установлен
    if not os.getenv("REGISTRATION_SECRET_WORD"):
        logger.warning(
            "REGISTRATION_SECRET_WORD is NOT SET — pharmacist registration will be blocked"
        )

    # Инициализация бота — каждый worker должен иметь свою копию bot/dp
    # потому что Gunicorn fork() не разделяет объекты между workers
    worker_pid = os.getpid()
    logger.info(f"Worker PID {worker_pid}: Initializing bot instance")

    # Каждый worker инициализирует своего бота (необходимо для обработки webhook)
    bot, dp = await bot_manager.initialize()

    if bot and dp:
        logger.info(f"Worker PID {worker_pid}: Bot initialized successfully")

        # Register middleware on specific event types to avoid breaking FSM middleware chain
        dp.message.middleware(DbMiddleware())
        dp.message.middleware(RoleMiddleware())
        dp.callback_query.middleware(DbMiddleware())
        dp.callback_query.middleware(RoleMiddleware())
        # Automatically answer all callback queries to prevent "unhandled" warnings
        dp.callback_query.middleware(CallbackAnswerMiddleware())
        dp.inline_query.middleware(DbMiddleware())
        dp.inline_query.middleware(RoleMiddleware())
        dp.chosen_inline_result.middleware(DbMiddleware())
        dp.chosen_inline_result.middleware(RoleMiddleware())
        dp.poll.middleware(DbMiddleware())
        dp.poll.middleware(RoleMiddleware())

        # Порядок роутеров важен: специфичные handlers ДО общих (unknown_command)
        dp.include_router(registration_router)
        dp.include_router(qa_handlers_router)
        dp.include_router(dialog_management_router)
        dp.include_router(user_questions_router)
        dp.include_router(clarify_router)
        dp.include_router(common_router)

        # УСТАНОВКА КОМАНД БОТА (только первый worker)
        init_lock_file = "/tmp/bot_commands_lock"
        if not os.path.exists(init_lock_file):
            try:
                fd = os.open(init_lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                try:
                    await set_bot_commands(bot)
                    logger.info("Bot commands set successfully")
                except Exception as e:
                    logger.error(f"Failed to set bot commands: {e}")
            except FileExistsError:
                pass  # Другой worker уже установил команды

        # УСТАНОВКА WEBHOOK ПРИ ЗАПУСКЕ (только первый worker)
        webhook_lock_file = "/tmp/webhook_lock"
        if not os.path.exists(webhook_lock_file):
            try:
                fd = os.open(webhook_lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                try:
                    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
                    secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")

                    if webhook_url:
                        current_info = await bot.get_webhook_info()
                        current_url = (
                            current_info.url if hasattr(current_info, "url") else None
                        )

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
            except FileExistsError:
                pass  # Другой worker уже установил webhook
        else:
            logger.info(f"Worker PID {worker_pid}: Webhook already configured by another worker")

        logger.info(f"Worker PID {worker_pid}: Bot ready to handle webhooks")
    else:
        logger.error(
            f"Worker PID {worker_pid}: Bot NOT initialized — Telegram features will be disabled!"
        )

    yield

    # Завершение работы бота (каждый worker закрывает своего бота)
    bot = bot_manager.get_bot()
    if bot:
        await bot_manager.shutdown()
        logger.info(f"Worker PID {os.getpid()}: Bot session closed")

        # УДАЛЕНИЕ WEBHOOK ПРИ ЗАВЕРШЕНИИ (только если это последний worker)
        # В production обычно не удаляем webhook при перезапуске
        # чтобы избежать downtime. Оставляем webhook активным.
        # Раскомментируйте если нужно удалять webhook:
        # try:
        #     await bot.delete_webhook(drop_pending_updates=True)
        #     logger.info("Webhook deleted on shutdown")
        # except Exception as e:
        #     logger.error(f"Error deleting webhook: {e}")


app = FastAPI(lifespan=lifespan, title="Novamedika Q&A Bot API")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Слишком много запросов. Попробуйте позже."},
    )


# Global exception handler — prevents leaking internals (SQL errors, paths, stack traces)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full details for debugging (server-side only)
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}"
    )
    # Generic message for client — no internals leaked
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ДОБАВИТЬ CORS MIDDLEWARE
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",")]
if not origins or origins == [""]:
    origins = [
        "http://localhost:3000",
        "https://spravka.novamedika.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Telegram-Bot-Api-Secret-Token",
    ],
)

# Подключение API роутеров
from routers import (
    pharmacist_auth,
    qa,
    telegram_bot,
    search,
    upload,
    pharmacies_info,
    pharmacist_dashboard,
)

app.include_router(pharmacist_auth.router, prefix="/api/pharmacist", tags=["auth"])
app.include_router(qa.router, tags=["qa"])
app.include_router(telegram_bot.router, tags=["bot"])
app.include_router(search.router, tags=["search"])
app.include_router(upload.router, tags=["upload"])
app.include_router(pharmacies_info.router, tags=["pharmacies"])
app.include_router(booking_orders.router, tags=["booking"])
app.include_router(pharmacy_api.router, tags=["pharmacy-api"])
app.include_router(pharmacist_dashboard.router, prefix="/api/pharmacist", tags=["pharmacist-dashboard"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "Novamedika Q&A Bot API"}


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}


@app.head("/health")
async def health_check_head():
    """HEAD request for health check (lightweight)."""
    from fastapi.responses import Response
    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
