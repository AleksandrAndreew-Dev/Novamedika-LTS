"""Сервис для работы с пользователями."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.qa_models import User

logger = logging.getLogger(__name__)


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    telegram_username: str | None = None,
    user_type: str = "customer",
) -> User | None:
    """Найти или создать пользователя по Telegram ID.

    Parameters
    ----------
    db : AsyncSession
    telegram_id : int
    first_name, last_name, telegram_username : str, optional
    user_type : str
        ``"customer"`` или ``"pharmacist"``. По умолчанию ``"customer"``.

    Returns
    -------
    User | None
        Найденный или созданный пользователь, либо ``None`` при ошибке.
    """
    try:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            telegram_username=telegram_username,
            user_type=user_type,
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info("Created new user with telegram_id: %d", telegram_id)
            return user
        except Exception:
            await db.rollback()
            logger.exception("Failed to create user for telegram_id: %d", telegram_id)
            return None

    except Exception:
        logger.exception("Error in get_or_create_user for telegram_id: %d", telegram_id)
        return None
