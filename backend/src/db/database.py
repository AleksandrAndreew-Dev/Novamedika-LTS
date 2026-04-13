# db/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg
import logging
from .base import Base

logger = logging.getLogger(__name__)

# Используем переменную из окружения или fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://novamedika:novamedika@postgres:5432/novamedika_prod",
)
ASYNCPG_DATABASE_URL = os.getenv(
    "ASYNCPG_DATABASE_URL",
    "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod",
)

# Создаем engine и sessionmaker при первом вызове
_engine = None
_async_session_maker = None


def get_engine():
    """Get or create async engine (thread-safe lazy initialization)"""
    return _get_or_create_engine()


def get_async_sessionmaker():
    """Get or create async sessionmaker (thread-safe lazy initialization)"""
    return _get_or_create_sessionmaker()


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


# Глобальные переменные для обратной совместимости (ленивая инициализация)
_engine = None
_async_session_maker = None


def _get_or_create_engine():
    """Get or create engine (called lazily)"""
    global _engine
    if _engine is None:
        echo = os.getenv("SQL_ECHO", "false").lower() == "true"
        _engine = create_async_engine(DATABASE_URL, echo=echo)
    return _engine


def _get_or_create_sessionmaker():
    """Get or create sessionmaker (called lazily)"""
    global _async_session_maker
    if _async_session_maker is None:
        engine = _get_or_create_engine()
        _async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


# Properties for backward compatibility (lazy evaluation)
class _LazyEngine:
    """Proxy object that creates engine on first access"""

    def __getattr__(self, name):
        return getattr(_get_or_create_engine(), name)


class _LazySessionMaker:
    """Proxy object that creates sessionmaker on first access"""

    def __getattr__(self, name):
        return getattr(_get_or_create_sessionmaker(), name)

    def __call__(self, *args, **kwargs):
        """Allow calling async_session_maker() directly — delegates to real sessionmaker"""
        return _get_or_create_sessionmaker()(*args, **kwargs)


engine = _LazyEngine()
async_session_maker = _LazySessionMaker()


# db/database.py - ДОБАВЬТЕ ЭТИ ФУНКЦИИ


async def get_async_session() -> AsyncSession:
    """Создает новую асинхронную сессию для использования в задачах"""
    session_maker = get_async_sessionmaker()
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()


async def execute_in_transaction(session: AsyncSession, query, **params):
    """Выполняет запрос в транзакции с обработкой ошибок"""
    async with session.begin():
        try:
            result = await session.execute(query, params)
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise


# database.py - ДОБАВЬТЕ ЭТИ ФУНКЦИИ

# db/database.py - ДОБАВЬТЕ ЭТИ ФУНКЦИИ


async def dispose_engine():
    """Явно закрывает все соединения engine с обработкой ошибок"""
    global _engine, _async_session_maker
    if _engine:
        try:
            await _engine.dispose()
            logger.info("Engine disposed successfully")
        except Exception as e:
            logger.error(f"Error disposing engine: {e}")
        finally:
            _engine = None
            _async_session_maker = None


def reset_engine():
    """Сбрасывает engine (для использования после fork)"""
    global _engine, _async_session_maker
    if _engine:
        logger.info("Resetting engine after fork")
    _engine = None
    _async_session_maker = None


# Переопределяем для явного вызова
def get_or_create_engine():
    """Public alias for lazy engine creation"""
    return _get_or_create_engine()


def get_or_create_sessionmaker():
    """Public alias for lazy sessionmaker creation"""
    return _get_or_create_sessionmaker()
