import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from routers.pharmacist_auth import get_pharmacist_by_telegram_id


logger = logging.getLogger(__name__)

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Update, Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        try:

        # Получаем реальное событие из Update если нужно
            if isinstance(event, Update):
                # Для Update получаем реальное событие (message, callback_query и т.д.)
                if event.message:
                    real_event = event.message
                elif event.callback_query:
                    real_event = event.callback_query
                elif event.edited_message:
                    real_event = event.edited_message
                else:
                    # Если это другой тип Update, который мы не обрабатываем, пропускаем
                    return await handler(event, data)
            else:
                real_event = event

            # Теперь работаем с реальным событием, которое имеет from_user
            if hasattr(real_event, "from_user") and real_event.from_user:
                    db = data["db"]
                    user_id = real_event.from_user.id

                    # Определяем тип пользователя
                    from routers.pharmacist_auth import get_pharmacist_by_telegram_id
                    pharmacist = await get_pharmacist_by_telegram_id(user_id, db)
                    data["is_pharmacist"] = pharmacist is not None
                    data["pharmacist"] = pharmacist
                    data["user_role"] = "pharmacist" if pharmacist else "customer"
                    data["user_id"] = user_id
            else:
                data["is_pharmacist"] = False
                data["pharmacist"] = None
                data["user_role"] = "unknown"
                data["user_id"] = None

                return await handler(event, data)
        except Exception as e:

            logger.error(f"RoleMiddleware error: {e}")
            # Устанавливаем значения по умолчанию при ошибке
            data["is_pharmacist"] = False
            data["pharmacist"] = None
            data["user_role"] = "customer"
            return await handler(event, data)
