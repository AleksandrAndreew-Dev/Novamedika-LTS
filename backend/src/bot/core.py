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

        from redis.asyncio import Redis
        redis_client = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False
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
            self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            self._storage = await self._create_storage()
            self.dp = Dispatcher(storage=self._storage)

            logger.info("Bot initialized successfully with RedisStorage")
            return self.bot, self.dp
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return None, None

    def get_bot(self) -> Bot | None:
        return self.bot

    def get_dp(self) -> Dispatcher | None:
        return self.dp

    async def shutdown(self):
        if self.bot:
            await self.bot.session.close()
        logger.info("Bot session closed")

# Глобальный экземпляр менеджера бота
bot_manager = BotManager()
