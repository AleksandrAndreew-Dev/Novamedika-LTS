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
    # В файле role_middleware.py исправьте функцию __call__:

    async def __call__(self, handler, event, data):
        """Основной обработчик middleware"""
        db = data.get("db")
        if not db:
            raise RuntimeError("Database session not found in data")

        user_id = None
        from_user = None

        # Определяем тип события и получаем from_user
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user
        elif isinstance(event, types.Poll):
            return await handler(event, data)

        if not from_user:
            return await handler(event, data)

        user_id = from_user.id

        try:
            user = await get_or_create_user(user_id, db)
            pharmacist = await get_pharmacist_by_user_id(user.uuid, db)
        except Exception as e:
            logger.error(f"Error in role middleware user processing for {user_id}")
            logger.error(e)
            # ❌ ИСПРАВЛЯЕМ: устанавливаем pharmacist в None вместо вызова raise
            pharmacist = None
            user = None  # также устанавливаем user в None
            # Продолжаем выполнение, но логируем ошибку

        logger.info(f"RoleMiddleware: User {user_id} - is_pharmacist: {pharmacist is not None}")

        # Добавляем данные в контекст
        data["user"] = user
        data["pharmacist"] = pharmacist
        data["is_pharmacist"] = pharmacist is not None

        return await handler(event, data)


