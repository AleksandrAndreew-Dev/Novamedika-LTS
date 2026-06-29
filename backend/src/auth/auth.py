import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Optional
from fastapi import Request

# Импорты из правильных мест
from db.database import get_db
from db.qa_models import Pharmacist, User
from db.token_models import RefreshToken
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Validate SECRET_KEY at module level
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = get_utc_now_naive() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY or "", algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Создать refresh token с отдельным сроком жизни"""
    to_encode = data.copy()
    expire = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY or "", algorithm=ALGORITHM)


async def get_current_pharmacist(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY or "", algorithms=[ALGORITHM]
        )
        # Проверяем что это access token (не refresh)
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        pharmacist_id = payload.get("sub")
        if pharmacist_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(Pharmacist)
        .options(selectinload(Pharmacist.user))
        .where(Pharmacist.uuid == pharmacist_id)
    )
    pharmacist = result.scalar_one_or_none()
    if pharmacist is None:
        raise HTTPException(status_code=401, detail="Pharmacist not found")

    # Check if pharmacist is active (handle SQLAlchemy column properly)
    if not getattr(pharmacist, "is_active", False):
        raise HTTPException(status_code=401, detail="Pharmacist account is deactivated")

    return pharmacist


async def store_refresh_token(token: str, user_id: str, db: AsyncSession):
    """Сохранить refresh token в БД (удаляет старые активные токены пользователя)"""
    from sqlalchemy.exc import IntegrityError

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Удаляем все активные токены пользователя перед созданием нового
            await db.execute(
                delete(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    getattr(RefreshToken, "revoked") == False,
                )
            )

            # Создаем новый токен
            expires_at = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = RefreshToken(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token=token,
                expires_at=expires_at,
                revoked=False,
            )
            db.add(refresh_token)
            await db.commit()
            await db.refresh(refresh_token)
            return refresh_token

        except IntegrityError as e:
            await db.rollback()
            logger.warning(
                f"IntegrityError on attempt {attempt + 1} for user {user_id}: {e}"
            )
            if attempt == max_attempts - 1:
                # If we still fail after retries, it means there's a persistent issue.
                # We can try to find an existing token and return it, or just raise.
                # For now, let's log and raise a more specific error.
                logger.error(
                    f"Failed to create refresh token after {max_attempts} attempts for user {user_id}"
                )
                raise HTTPException(
                    status_code=500, detail="Unable to generate unique refresh token"
                )


async def revoke_refresh_token(token: str, db: AsyncSession):
    """Отозвать refresh token по токену"""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    rt = result.scalar_one_or_none()

    if rt:
        setattr(rt, "revoked", True)
        await db.commit()


async def validate_refresh_token(token: str, db: AsyncSession):
    """Проверить валидность refresh token"""
    try:
        payload = jwt.decode(token, SECRET_KEY or "", algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except (ExpiredSignatureError, InvalidTokenError):
        return None

    # Проверяем наличие в БД и статус отзыва
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token, getattr(RefreshToken, "revoked") == False
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        return None

    return user_id


async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Получить текущего пользователя из JWT токена

    Используется для аутентификации обычных пользователей (не фармацевтов)
    через веб-приложение.
    """
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY or "", algorithms=[ALGORITHM]
        )

        # Проверяем что это access token (не refresh)
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Получаем пользователя из базы данных
    result = await db.execute(select(User).where(User.uuid == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user_jwt_or_tma(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Получить пользователя через JWT или TMA (Telegram Mini App) auth.

    Порядок проверки:
    1. Если есть JWT Bearer token — используем get_current_user_jwt
    2. Если есть TMA initData в Authorization (tma <data>) — валидируем
    3. Если ничего нет — возвращаем None (анонимный доступ)

    Используется для /api/consultations/ endpoints,
    где пользователи могут быть из Telegram Web App или обычные JWT.
    """

    # Try 1: Standard JWT Bearer
    if credentials:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                return await get_current_user_jwt(credentials=credentials, db=db)
            except HTTPException:
                logger.warning("JWT auth failed, trying TMA...")

    # Try 2: TMA (Telegram Mini App) auth
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("tma "):
        tma_init_data = auth_header[4:]  # Remove "tma " prefix
        logger.info(f"TMA auth attempt with init data length: {len(tma_init_data)}")

        try:
            # TMA validation typically happens via bot's webhook validation
            # For now, log and let anonymous fallback handle it
            logger.info("TMA validation stub — falls through to anonymous")
        except Exception as e:
            logger.warning(f"TMA auth failed: {e}")

    # Try 3: Check if user is in request scope (set by middleware)
    if hasattr(request, "user"):
        user = getattr(request, "user", None)
        if user:
            return user

    # No auth — return None for optional auth
    logger.info("No auth credentials found, returning None (anonymous)")
    return None
