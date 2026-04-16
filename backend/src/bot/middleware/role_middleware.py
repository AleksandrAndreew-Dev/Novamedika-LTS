from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, Poll
from typing import Callable, Dict, Any, Awaitable, Union, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from db.qa_models import Pharmacist, User
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)


async def get_pharmacist_by_telegram_id(
    telegram_id: int, db: AsyncSession
) -> Optional[Pharmacist]:
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == telegram_id)
            .where(Pharmacist.is_active == True)
        )
        return result.scalars().one_or_none()
    except Exception:
        logger.exception("Error getting pharmacist by telegram_id %s", telegram_id)
        return None


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [Union[Update, Message, CallbackQuery, Poll], Dict[str, Any]],
            Awaitable[Any],
        ],
        event: Union[Update, Message, CallbackQuery, Poll],
        data: Dict[str, Any],
    ) -> Any:
        """Основной обработчик middleware"""
        db = data.get("db")
        if not db:
            raise RuntimeError("Database session not found in data")

        user_id = None
        from_user = None

        # Определяем тип события и получаем from_user
        if isinstance(event, Update):
            if event.message:
                from_user = event.message.from_user
            elif event.callback_query:
                from_user = event.callback_query.from_user
            elif event.poll:
                # Для Poll нет from_user, пропускаем middleware
                return await handler(event, data)
            else:
                # Неизвестный тип обновления, пропускаем
                return await handler(event, data)
        elif isinstance(event, (Message, CallbackQuery)):
            from_user = event.from_user
        elif isinstance(event, Poll):
            # Для Poll нет from_user, пропускаем middleware
            return await handler(event, data)
        else:
            # Неизвестный тип события, пропускаем
            return await handler(event, data)

        if not from_user:
            return await handler(event, data)

        user_id = from_user.id

        try:
            user = await get_or_create_user(db, telegram_id=user_id)
            pharmacist = await get_pharmacist_by_telegram_id(user_id, db)
        except Exception as e:
            logger.error(f"Error in role middleware user processing for {user_id}: {e}")
            # В случае ошибки БД создаем "фейкового" пользователя, чтобы хендлер не упал
            # Или лучше пробросить ошибку, если это критично
            user = None
            pharmacist = None

        if not user:
            logger.warning(f"User {user_id} not found or created. Skipping message.")
            # Можно ответить пользователю, но лучше просто пропустить, чтобы не спамить
            return

        logger.info(
            f"RoleMiddleware: User {user_id} - is_pharmacist: {pharmacist is not None}"
        )

        # Добавляем данные в контекст
        data["user"] = user
        data["pharmacist"] = pharmacist
        data["is_pharmacist"] = pharmacist is not None

        return await handler(event, data)
