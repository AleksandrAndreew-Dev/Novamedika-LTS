import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand  # Добавьте этот импорт
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core import bot_manager
from bot.handlers import (
    direct_questions_router,
    common_router,
    registration_router,
    user_questions_router,
    qa_handlers_router,
)
from bot.middleware.role_middleware import RoleMiddleware
from db.database import init_models, async_session_maker
from bot.middleware.db import DbMiddleware

from routers import orders as booking_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):  # Теперь Bot импортирован
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
    # Инициализация бота при запуске
    await init_models()
    bot, dp = await bot_manager.initialize()

    if not bot or not dp:
        logger.error("Failed to initialize bot")
        return

    # УСТАНОВКА КОМАНД БОТА
    try:
        await set_bot_commands(bot)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # ПОДКЛЮЧЕНИЕ MIDDLEWARE
    dp.update.outer_middleware(DbMiddleware())
    dp.update.outer_middleware(RoleMiddleware())

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(qa_handlers_router)
    dp.include_router(user_questions_router)
    dp.include_router(direct_questions_router)


    # УСТАНОВКА WEBHOOK ПРИ ЗАПУСКЕ
    try:
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")

        if webhook_url:
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
            logger.error("TELEGRAM_WEBHOOK_URL not set")

    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

    logger.info("Bot started successfully with webhook")

    yield

    # Завершение работы бота
    await bot_manager.shutdown()

    # УДАЛЕНИЕ WEBHOOK ПРИ ЗАВЕРШЕНИИ
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted on shutdown")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")

app = FastAPI(lifespan=lifespan, title="Novamedika Q&A Bot API")

# ДОБАВИТЬ CORS MIDDLEWARE
origins = os.getenv("CORS_ORIGINS", "").split(",")
if not origins or origins == [""]:
    origins = ["http://localhost:3000", "https://spravka.novamedika.com",
               "https://booking.novamedika.com"
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
app.include_router(booking_router.router, tags=["booking"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Novamedika Q&A Bot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
