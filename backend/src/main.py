import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.common_handlers import router as common_router
from bot.handlers.registration_handlers import router as registration_router
from bot.handlers.user_questions_handlers import router as user_questions_router
from bot.handlers.qa_handlers import router as qa_handlers_router
from bot.middleware.db_middleware import DbMiddleware
from bot.middleware.role_middleware import RoleMiddleware
from bot.db import create_engine, create_session_maker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

token = os.getenv("TELEGRAM_BOT_TOKEN")

async def main():
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключение к базе данных
    engine = create_engine()
    session_maker = create_session_maker(engine)

    # Подключение middleware
    dp.update.middleware(DbMiddleware(session_maker))
    dp.update.middleware(RoleMiddleware())

    # Регистрация роутеров в правильном порядке
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(qa_handlers_router)  # Важно: до user_questions_router!
    dp.include_router(user_questions_router)

    logger.info("Bot started with updated router order")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
