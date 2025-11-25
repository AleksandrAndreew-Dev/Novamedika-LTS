# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg
import logging

# Импортируем Base из отдельного файла
from .base import Base

DATABASE_URL = "postgresql+asyncpg://novamedika:novamedika@postgres:5432/novamedika_prod"

logger = logging.getLogger(__name__)

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_models():
    """Инициализация моделей для предотвращения проблем с mapper'ами"""
    try:
        async with engine.begin() as conn:
            # Это заставит SQLAlchemy инициализировать все mapper'ы
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database models initialized successfully")
    except Exception as e:
        logger.warning(f"Models initialization warning: {e}")

async def get_db():
    async with async_session_maker() as session:
        yield session

async def get_async_connection():
    """Получить asyncpg соединение"""
    return await asyncpg.connect(
        "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod"
    )
