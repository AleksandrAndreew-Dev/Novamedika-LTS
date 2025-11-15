
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

class BotManager:
    _instance = None
    _bot = None
    _dp = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
        return cls._instance

    async def initialize(self):
        """Инициализация бота один раз при старте приложения"""
        if self._bot is not None:
            return self._bot, self._dp

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return None, None

        try:
            # Создаем бота с настройками для production
            self._bot = Bot(
                token=token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Для production рекомендуется RedisStorage вместо MemoryStorage
            storage = MemoryStorage()  # В будущем заменить на RedisStorage
            self._dp = Dispatcher(storage=storage)

            logger.info("Bot initialized successfully")
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
            await self._bot.session.close()
            self._bot = None
            self._dp = None

# Глобальный экземпляр менеджера
bot_manager = BotManager()
