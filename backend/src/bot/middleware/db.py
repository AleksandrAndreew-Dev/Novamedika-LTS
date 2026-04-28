from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, Poll
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session_maker

import logging

logger = logging.getLogger(__name__)


# Добавить эту функцию
def get_session() -> AsyncSession:
    """Получить сессию БД (для использования вне middleware)"""
    return async_session_maker()


class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [Union[Update, Message, CallbackQuery, Poll], Dict[str, Any]],
            Awaitable[Any],
        ],
        event: Union[Update, Message, CallbackQuery, Poll],
        data: Dict[str, Any],
    ) -> Any:
        logger.debug(f"DbMiddleware: Starting for event type={type(event).__name__}")
        
        async with async_session_maker() as session:
            data["db"] = session
            logger.debug("DbMiddleware: Injected 'db' session into data dict")
            
            try:
                result = await handler(event, data)
                logger.debug("DbMiddleware: Handler executed successfully, committing transaction")
                await session.commit()
                return result
            except Exception as e:
                logger.error(f"DbMiddleware: Rolling back due to error: {e}", exc_info=True)
                await session.rollback()
                raise
            finally:
                logger.debug("DbMiddleware: Closing database session")
                await session.close()
