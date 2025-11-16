from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

# Добавляем импорт для получения сессии БД
from db.database import get_db
from db.qa_models import Pharmacist, User
from utils.time_utils import get_utc_now_naive

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = get_utc_now_naive() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_pharmacist(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        pharmacist_id: str = payload.get("sub")
        if pharmacist_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Теперь selectinload будет работать
    result = await db.execute(
        select(Pharmacist)
        .options(selectinload(Pharmacist.user), selectinload(Pharmacist.pharmacy))
        .where(Pharmacist.uuid == pharmacist_id)
    )
    pharmacist = result.scalar_one_or_none()
    if pharmacist is None:
        raise HTTPException(status_code=401, detail="Pharmacist not found")

    if not pharmacist.is_active:
        raise HTTPException(status_code=401, detail="Pharmacist account is deactivated")

    return pharmacist
