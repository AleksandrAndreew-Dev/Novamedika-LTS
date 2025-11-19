from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session_maker

class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Update, Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['db'] = session
            return await handler(event, data)


class UserTypeMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        db = data['db']
        user_id = event.from_user.id

        # Определяем тип пользователя
        pharmacist = await get_pharmacist_by_telegram_id(user_id, db)
        data['is_pharmacist'] = pharmacist is not None
        data['pharmacist'] = pharmacist

        return await handler(event, data)
