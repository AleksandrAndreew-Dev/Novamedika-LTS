from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from sqlalchemy.exc import IntegrityError
from typing import Optional

from db.qa_models import Pharmacist, User


import uuid

logger = logging.getLogger(__name__)


# ЗАМЕНИТЬ эту функцию в role_middleware.py
async def get_or_create_user(telegram_id: int, db: AsyncSession) -> User:
    try:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        # Создаем нового пользователя с правильными полями
        new_user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_id,
            first_name=None,
            last_name=None,
            telegram_username=None,
            user_type="customer"
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Created new user with telegram_id: {telegram_id}")
        return new_user

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in get_or_create_user for {telegram_id}: {e}")
        raise


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
        # Лучше ожидать max 1 запись; однообразное поведение при отсутствии/дубликатах
        return result.scalars().one_or_none()
    except Exception:
        logger.exception("Error getting pharmacist by telegram_id %s", telegram_id)
        return None


class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: Dict[str, Any]):
        # defaults — всегда ставим ключи
        data.setdefault("is_pharmacist", False)
        data.setdefault("pharmacist", None)
        data.setdefault("user_role", "customer")
        data.setdefault("user", None)
        data.setdefault("user_id", None)

        real_event = event
        if isinstance(event, Update):
            # предпочитаем последовательность: message, edited_message, callback_query
            real_event = event.message or event.edited_message or event.callback_query
            if real_event is None:
                return await handler(event, data)

        if not getattr(real_event, "from_user", None):
            return await handler(event, data)

        db = data.get("db")
        if not (hasattr(db, "execute") and hasattr(db, "commit")):
            logger.error("Database session not found or invalid in data")
            return await handler(event, data)

        user_id = real_event.from_user.id
        data["user_id"] = user_id

        try:
            user = await get_or_create_user(user_id, db)
            pharmacist = await get_pharmacist_by_telegram_id(user_id, db)

            data["user"] = user
            data["is_pharmacist"] = pharmacist is not None
            data["pharmacist"] = pharmacist
            data["user_role"] = "pharmacist" if pharmacist else "customer"

            logger.debug(
                "Role middleware: user %s is_pharmacist=%s",
                user_id,
                pharmacist is not None,
            )
        except Exception:
            logger.exception("Error in role middleware user processing for %s", user_id)
            # оставить defaults, не прерываем поток

        return await handler(event, data)
