import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class BotManager:
    _instance = None
    _bot = None
    _dp = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def is_initialized(self):
        return self._bot is not None and self._dp is not None

    async def _create_storage(self):
        """Создает RedisStorage для FSM или fallback на MemoryStorage"""
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_password = os.getenv("REDIS_PASSWORD", "")
        redis_db = 1  # DB 0 — Celery, DB 1 — Bot FSM

        redis_url = f"redis://:{redis_password}@{redis_host}:6379/{redis_db}"

        try:
            # Создаем Redis клиент для FSM storage
            redis_client = redis.from_url(
                redis_url, health_check_interval=10, decode_responses=True
            )
            # Проверяем подключение
            await redis_client.ping()
            logger.info(
                f"Using RedisStorage for bot FSM: redis://{redis_host}:6379/{redis_db}"
            )
            # Aiogram 3.x требует Redis объект, а не URL строку
            return RedisStorage(redis_client)
        except Exception as e:
            logger.warning(
                f"Redis unavailable for bot FSM ({e}), falling back to MemoryStorage. "
                "FSM states will be lost on restart."
            )
            return MemoryStorage()

    async def ensure_initialized(self):
        if not await self.is_initialized():
            return await self.initialize()
        return self._bot, self._dp

    async def initialize(self):
        """Инициализация бота один раз при старте приложения — thread-safe."""
        async with self._lock:
            if self._bot is not None:
                return self._bot, self._dp

            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN not set")
                return None, None

            try:
                # Создаем бота с настройками для production
                self._bot = Bot(
                    token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )

                # Проверяем, что бот доступен
                bot_info = await self._bot.get_me()
                logger.info(f"Bot initialized successfully: @{bot_info.username}")

                # Production: RedisStorage для сохранения FSM состояний при рестарте
                storage = await self._create_storage()
                self._dp = Dispatcher(storage=storage)

                return self._bot, self._dp

            except Exception as e:
                logger.error(f"Failed to initialize bot: {str(e)}")
                return None, None

    def get_bot(self):
        return self._bot

    def get_dispatcher(self):
        return self._dp

    async def shutdown(self):
        """Корректное завершение работы бота"""
        if self._bot:
            try:
                # Закрываем сессию бота
                await self._bot.session.close()
                # Также закрываем внутреннюю сессию aiohttp
                if hasattr(self._bot, "_session") and self._bot._session:
                    await self._bot._session.close()
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")
            finally:
                self._bot = None
                self._dp = None
                logger.info("Bot shutdown completed")


# Глобальный экземпляр менеджера
bot_manager = BotManager()
