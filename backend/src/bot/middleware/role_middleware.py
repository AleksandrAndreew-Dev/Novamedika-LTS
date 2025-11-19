# bot/middleware/role_middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from routers.pharmacist_auth import get_pharmacist_by_telegram_id

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        db = data['db']
        user_id = event.from_user.id

        # Определяем тип пользователя
        pharmacist = await get_pharmacist_by_telegram_id(user_id, db)
        data['is_pharmacist'] = pharmacist is not None
        data['pharmacist'] = pharmacist
        data['user_role'] = 'pharmacist' if pharmacist else 'customer'

        return await handler(event, data)
