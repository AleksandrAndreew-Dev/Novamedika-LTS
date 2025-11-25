# db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg
import logging

# Import Base and all models to ensure they are registered
from .base import Base
from . import models, booking_models, qa_models  # This ensures all models are imported

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+asyncpg://novamedika:novamedika@postgres:5432/novamedika_prod"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_models():
    """Initialize database models"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database models initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing models: {e}")
        raise

async def get_db():
    async with async_session_maker() as session:
        yield session

async def get_async_connection():
    """Get asyncpg connection"""
    return await asyncpg.connect(
        "postgresql://novamedika:novamedika@postgres:5432/novamedika_prod"
    )
