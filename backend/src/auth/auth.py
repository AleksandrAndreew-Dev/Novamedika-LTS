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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Создать refresh token с отдельным сроком жизни"""
    to_encode = data.copy()
    expire = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_pharmacist(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        # Проверяем что это access token (не refresh)
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        pharmacist_id: str = payload.get("sub")
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
    if not getattr(pharmacist, 'is_active', False):
        raise HTTPException(status_code=401, detail="Pharmacist account is deactivated")

    return pharmacist


async def store_refresh_token(token: str, user_id: str, db: AsyncSession):
    """Сохранить refresh token в БД (удаляет старые активные токены пользователя)"""
    from sqlalchemy.exc import IntegrityError
    
    # Удаляем все активные токены пользователя перед созданием нового
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        )
    )
    
    # Добавляем уникальный идентификатор к токену для предотвращения дублирования
    # Это особенно важно при параллельных запросах
    jti = str(uuid.uuid4())
    unique_token = f"{token}_{jti}"
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Создаем новый токен
            expires_at = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = RefreshToken(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token=unique_token,  # Используем уникальный токен
                expires_at=expires_at,
                revoked=False,
            )
            db.add(refresh_token)
            await db.commit()
            await db.refresh(refresh_token)
            return refresh_token
            
        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"IntegrityError on attempt {attempt + 1} for user {user_id}: {e}")
            if attempt == max_attempts - 1:
                logger.error(f"Failed to create unique refresh token after {max_attempts} attempts for user {user_id}")
                raise HTTPException(status_code=500, detail="Unable to generate unique refresh token")
            # Генерируем новый уникальный токен для следующей попытки
            jti = str(uuid.uuid4())
            unique_token = f"{token}_{jti}"


async def revoke_refresh_token(token: str, db: AsyncSession):
    """Отозвать refresh token по токену"""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


async def validate_refresh_token(token: str, db: AsyncSession):
    """Проверить валидность refresh token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except (ExpiredSignatureError, InvalidTokenError):
        return None

    # Проверяем наличие в БД и статус отзыва
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked == False
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        return None

    return user_id