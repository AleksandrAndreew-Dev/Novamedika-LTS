import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Redis Storage для FSM (Memory Bank)
async def _create_storage():
    """Создает RedisStorage для FSM или fallback на MemoryStorage"""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 1))

    # Создаем Redis клиент для FSM storage
    from redis.asyncio import Redis
    redis_client = Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=False
    )

    # Проверяем подключение к Redis
    try:
        await redis_client.ping()
        logger.info(
            f"Using RedisStorage for bot FSM: redis://{redis_host}:{redis_port}/{redis_db}"
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    # Создаем RedisStorage с объектом Redis, а не строкой URL
    # (требование aiogram 3.x)
    return RedisStorage(redis_client)

# Основная функция инициализации бота
async def init_bot(token: str):
    """Инициализирует бота с Redis Storage для FSM"""
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = await _create_storage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware и обработчиков
    # ... (остальная конфигурация)

    logger.info("Bot initialized successfully with RedisStorage")
    return bot, dp
