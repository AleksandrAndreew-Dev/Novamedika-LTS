import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self._storage: RedisStorage | None = None

    async def _create_storage(self):
        """Создает RedisStorage для FSM"""
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 1))
        redis_password = os.getenv("REDIS_PASSWORD", None)

        from redis.asyncio import Redis

        # Создаем клиент Redis с учетом пароля
        redis_client = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,  # <-- Добавлено
            decode_responses=False,
        )

        try:
            await redis_client.ping()
            logger.info(
                f"Using RedisStorage for bot FSM: redis://{redis_host}:{redis_port}/{redis_db}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        return RedisStorage(redis_client)

    async def initialize(self):
        """Инициализирует бота с Redis Storage для FSM"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not set. Bot will not be initialized.")
            return None, None

        try:
            self.bot = Bot(
                token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            # Переиспользуем существующий Dispatcher, если он уже был создан.
            # Это необходимо для корректного auto-restart после /qa/drop:
            # роутеры уже зарегистрированы в старом dp, и повторный include_router
            # вызовет ошибку "Router is already attached".
            if not self.dp:
                self._storage = await self._create_storage()
                self.dp = Dispatcher(storage=self._storage)
                # Настраиваем middleware и роутеры только для нового Dispatcher
                await self._setup_dispatcher()
                logger.info(
                    "Bot initialized successfully with RedisStorage (new dispatcher)"
                )
            else:
                logger.info(
                    "Bot initialized successfully with RedisStorage (reused dispatcher)"
                )
            return self.bot, self.dp
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return None, None

    async def _setup_dispatcher(self):
        """Настройка middleware и роутеров для dispatcher"""
        from bot.middleware.role_middleware import RoleMiddleware
        from bot.middleware.db import DbMiddleware
        from aiogram.utils.callback_answer import CallbackAnswerMiddleware
        from bot.handlers import (
            registration_router,
            qa_handlers_router,
            dialog_management_router,
            user_questions_router,
            common_router,
        )
        from bot.handlers.clarify_handlers import router as clarify_router

        # Register middleware
        self.dp.message.middleware(DbMiddleware())
        self.dp.message.middleware(RoleMiddleware())
        self.dp.callback_query.middleware(DbMiddleware())
        self.dp.callback_query.middleware(RoleMiddleware())
        self.dp.callback_query.middleware(CallbackAnswerMiddleware())
        self.dp.inline_query.middleware(DbMiddleware())
        self.dp.inline_query.middleware(RoleMiddleware())
        self.dp.chosen_inline_result.middleware(DbMiddleware())
        self.dp.chosen_inline_result.middleware(RoleMiddleware())
        self.dp.poll.middleware(DbMiddleware())
        self.dp.poll.middleware(RoleMiddleware())

        # Include routers
        self.dp.include_router(registration_router)
        self.dp.include_router(qa_handlers_router)
        self.dp.include_router(dialog_management_router)
        self.dp.include_router(user_questions_router)
        self.dp.include_router(clarify_router)
        self.dp.include_router(common_router)

        logger.info("Dispatcher middleware and routers configured")

    def get_bot(self) -> Bot | None:
        return self.bot

    def get_dp(self) -> Dispatcher | None:
        return self.dp

    async def reset(self):
        """Сброс бота и FSM storage для auto-restart после /qa/drop"""
        logger.warning(
            "🔄 BotManager reset initiated — cleaning up FSM storage and bot instances"
        )

        # Закрываем FSM storage
        if self._storage:
            try:
                redis_client = self._storage.redis
                if redis_client:
                    await redis_client.flushdb()
                    logger.info("Redis FSM storage flushed (DB 1 cleared)")
            except Exception as e:
                logger.warning(f"Redis FSM flush error (non-critical): {e}")
            try:
                await self._storage.close()
            except Exception as e:
                logger.warning(f"FSM storage close error (non-critical): {e}")
            self._storage = None

        # Закрываем bot session
        if self.bot:
            try:
                await self.bot.session.close()
            except Exception as e:
                logger.warning(f"Bot session close error (non-critical): {e}")
            self.bot = None

        # Dispatcher НЕ обнуляем — роутеры уже зарегистрированы, и повторный
        # include_router вызовет ошибку "Router is already attached".
        # При следующем initialize() создастся новый Bot, а Dispatcher переиспользуется.
        logger.warning(
            "✅ BotManager reset complete — dp preserved, will reinitialize on next webhook"
        )

    async def shutdown(self):
        if self.bot:
            await self.bot.session.close()
        logger.info("Bot session closed")


# Глобальный экземпляр менеджера бота
bot_manager = BotManager()
