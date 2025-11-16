# bot/middleware/db.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery  # Импортируйте отсюда
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session_maker

class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['db'] = session
            return await handler(event, data)
