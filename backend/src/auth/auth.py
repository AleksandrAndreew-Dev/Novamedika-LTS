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

SECRET_KEY = os.getenv("SECRET_KEY")
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

    if not pharmacist.is_active:
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
    
    try:
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
        return refresh_token
    except IntegrityError as e:
        # Если возникла ошибка уникальности (конкурентный запрос),
        # откатываем и проверяем, существует ли уже токен
        await db.rollback()
        
        # Проверяем, существует ли уже этот токен
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        existing_token = result.scalar_one_or_none()
        
        if existing_token:
            # Токен уже существует (создан другим запросом), возвращаем его
            logger.info(f"Refresh token already exists for user {user_id}, using existing token")
            return existing_token
        else:
            # Другая ошибка уникальности, пробуем еще раз
            logger.warning(f"IntegrityError during token creation, retrying: {e}")
            
            # Повторяем попытку
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
            return refresh_token


async def revoke_refresh_token(token: str, db: AsyncSession):
    """Отозвать refresh token (logout)"""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


async def validate_refresh_token(token: str, db: AsyncSession) -> dict:
    """Проверить refresh token: decode + проверить в БД"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Проверяем в БД что токен не отозван
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > get_utc_now_naive(),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Token revoked or expired")

    return {"user_id": user_id}
