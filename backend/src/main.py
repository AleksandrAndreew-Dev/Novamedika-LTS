import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core import bot_manager
from bot.handlers import common_router, registration_router, user_questions_router, qa_handlers_router
from bot.middleware.role_middleware import RoleMiddleware
from db.database import async_session_maker
from bot.middleware.db import DbMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация бота при запуске
    bot, dp = await bot_manager.initialize()
    if not bot or not dp:
        logger.error("Failed to initialize bot")
        return

    # Подключение middleware
    dp.update.middleware(DbMiddleware(async_session_maker))
    dp.update.middleware(RoleMiddleware())

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(qa_handlers_router)
    dp.include_router(user_questions_router)

    logger.info("Bot started successfully")

    yield

    # Завершение работы бота
    await bot_manager.shutdown()

app = FastAPI(lifespan=lifespan)

# Подключение API роутеров
from routers import pharmacist_auth, qa, telegram_bot

app.include_router(pharmacist_auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(qa.router, prefix="/api/qa", tags=["qa"])
app.include_router(telegram_bot.router, prefix="/api/bot", tags=["bot"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Novamedika Q&A Bot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
