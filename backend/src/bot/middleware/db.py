# bot/middleware/db.py
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable, Message
from db.database import async_session_maker

class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['session'] = session
            return await handler(event, data)
