# Исправленная версия role_middleware.py
from routers.pharmacist_auth import get_pharmacist_by_telegram_id
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession



logger = logging.getLogger(__name__)

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Update, Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        try:
            # Получаем реальное событие
            real_event = event
            if isinstance(event, Update):
                if event.message:
                    real_event = event.message
                elif event.callback_query:
                    real_event = event.callback_query
                elif event.edited_message:
                    real_event = event.edited_message
                else:
                    return await handler(event, data)

            # Проверяем наличие from_user
            if not hasattr(real_event, "from_user") or not real_event.from_user:
                data["is_pharmacist"] = False
                data["pharmacist"] = None
                data["user_role"] = "unknown"
                data["user_id"] = None
                return await handler(event, data)

            # Определяем тип пользователя
            db = data.get("db")
            if not db:
                logger.error("Database session not found in data")
                data["is_pharmacist"] = False
                data["pharmacist"] = None
                return await handler(event, data)

            user_id = real_event.from_user.id
            pharmacist = await get_pharmacist_by_telegram_id(user_id, db)

            data["is_pharmacist"] = pharmacist is not None
            data["pharmacist"] = pharmacist
            data["user_role"] = "pharmacist" if pharmacist else "customer"
            data["user_id"] = user_id

            return await handler(event, data)

        except Exception as e:
            logger.error(f"RoleMiddleware error: {e}")
            data["is_pharmacist"] = False
            data["pharmacist"] = None
            data["user_role"] = "customer"
            return await handler(event, data)

# role_middleware.py - ДОБАВИТЬ ЭТУ ФУНКЦИЮ
async def get_pharmacist_by_telegram_id(telegram_id: int, db):
    """Найти фармацевта по Telegram ID"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from db.qa_models import Pharmacist, User

    result = await db.execute(
        select(Pharmacist)
        .join(User, Pharmacist.user_id == User.uuid)
        .options(selectinload(Pharmacist.user))
        .where(User.telegram_id == telegram_id)
        .where(Pharmacist.is_active == True)
    )
    return result.scalars().first()
