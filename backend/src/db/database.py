# db/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg
import logging
from .base  import Base

logger = logging.getLogger(__name__)

# Используем переменную из окружения или fallback
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql+asyncpg://novamedika:novamedika@postgres:5432/novamedika_prod")
ASYNCPG_DATABASE_URL = os.getenv('ASYNCPG_DATABASE_URL', "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod")

# Создаем engine и sessionmaker при первом вызове
_engine = None
_async_session_maker = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=True)
    return _engine

def get_async_sessionmaker():
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_maker

async def init_models():
    """Initialize database models"""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database models initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing models: {e}")
        raise

async def get_db():
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        yield session

async def get_async_connection():
    """Get asyncpg connection"""
    return await asyncpg.connect(ASYNCPG_DATABASE_URL)

# Глобальные переменные для обратной совместимости
engine = get_engine()
async_session_maker = get_async_sessionmaker()
