# database.py - дополнить
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg

DATABASE_URL = "postgresql+asyncpg://novamedika:novamedika@postgres:5432/novamedika_prod"

Base = declarative_base()

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session_maker() as session:
        yield session

async def get_async_connection():
    """Получить asyncpg соединение"""
    return await asyncpg.connect(
        "postgresql://novamedika:novamedika@postgres:5432/novamedika_dev"
    )
