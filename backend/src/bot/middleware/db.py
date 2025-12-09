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
        handler: Callable[[Union[Update, Message, CallbackQuery, Poll], Dict[str, Any]], Awaitable[Any]],
        event: Union[Update, Message, CallbackQuery, Poll],
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['db'] = session
            try:
                result = await handler(event, data)

                # Проверяем, не было ли исключения в обработчике
                if not session.in_transaction():
                    await session.commit()
                elif session.is_active:
                    try:
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Error committing transaction: {e}")

                return result
            except Exception as e:
                # Если сессия все еще активна, откатываем
                if session.is_active:
                    await session.rollback()
                logger.error(f"Error in handler: {e}")
                raise e
            finally:
                await session.close()
