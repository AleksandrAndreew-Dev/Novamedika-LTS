from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid
import logging

from db.database import get_db
from db.qa_models import User, Pharmacist
from services.user_service import get_or_create_user
from db.qa_schemas import (
    PharmacistCreate,
    PharmacistResponse,
    UserResponse,
    PharmacyInfoSimple,
)
from auth.auth import (
    create_access_token,
    create_refresh_token,
    get_current_pharmacist,
    store_refresh_token,
    revoke_refresh_token,
    validate_refresh_token,
)
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)
router = APIRouter()


# Новая функция для получения фармацевта по Telegram ID
async def get_pharmacist_by_telegram_id(
    telegram_id: int, db: AsyncSession
) -> Pharmacist:
    """Найти фармацевта по Telegram ID"""
    result = await db.execute(
        select(Pharmacist)
        .join(User, Pharmacist.user_id == User.uuid)
        .options(selectinload(Pharmacist.user))
        .where(User.telegram_id == telegram_id)
        .where(Pharmacist.is_active == True)
    )
    return result.scalars().first()


@router.post("/register-from-telegram/", response_model=PharmacistResponse)
@limiter.limit("5/minute")
async def register_pharmacist(
    request: Request,
    telegram_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация фармацевта с проверкой дубликатов (rate limit 5/min)"""
    try:
        user = await get_or_create_user(
            db,
            telegram_id=telegram_data["telegram_user_id"],
            first_name=telegram_data.get("first_name"),
            last_name=telegram_data.get("last_name"),
            telegram_username=telegram_data.get("telegram_username"),
            user_type="pharmacist",
        )
        pharmacy_info = telegram_data.get("pharmacy_info", {})

        # ПРОВЕРКА ДУБЛИКАТОВ - ИСПРАВЛЕННАЯ ВЕРСИЯ
        result = await db.execute(
            select(Pharmacist)
            .where(Pharmacist.user_id == user.uuid)
            .where(
                Pharmacist.pharmacy_info["name"].as_string()
                == pharmacy_info.get("name")
            )
        )
        existing_pharmacist = result.scalar_one_or_none()

        if existing_pharmacist:
            # Если запись уже есть, активируем ее
            existing_pharmacist.is_active = True
            existing_pharmacist.is_online = True
            existing_pharmacist.last_seen = get_utc_now_naive()
            pharmacist = existing_pharmacist
        else:
            # Создаем новую запись
            pharmacist = Pharmacist(
                uuid=uuid.uuid4(),
                user_id=user.uuid,
                pharmacy_info=pharmacy_info,
                is_active=True,
                is_online=True,
                last_seen=get_utc_now_naive(),
            )
            db.add(pharmacist)

        await db.commit()
        await db.refresh(pharmacist)

        return PharmacistResponse(
            uuid=pharmacist.uuid,
            user=UserResponse.model_validate(user),
            pharmacy_info=PharmacyInfoSimple(**pharmacy_info),
            is_active=pharmacist.is_active,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/")
@limiter.limit("10/minute")
async def pharmacist_login(
    request: Request,
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Логин фармацевта по Telegram ID (поддерживает несколько аптек)"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == telegram_user_id)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            raise HTTPException(status_code=404, detail="Фармацевт не найден")

        # Берем первого активного фармацевта
        pharmacist = pharmacists[0]

        # Обновляем статус онлайн и время последней активности
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()

        # Если нужно, можно вернуть список всех аптек для выбора
        if len(pharmacists) > 1:
            logger.info(
                f"User {telegram_user_id} has {len(pharmacists)} active pharmacist profiles"
            )

        # Создаём JWT токены
        token_data = {"sub": str(pharmacist.uuid), "type": "access"}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"sub": str(pharmacist.uuid)})

        # Сохраняем refresh token в БД
        await store_refresh_token(refresh_token, str(pharmacist.uuid), db)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 минут
            "pharmacist": PharmacistResponse(
                uuid=pharmacist.uuid,
                user=UserResponse.model_validate(pharmacist.user),
                pharmacy_info=pharmacist.pharmacy_info,
                is_active=pharmacist.is_active,
            ),
            "total_pharmacies": len(pharmacists),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=PharmacistResponse)
async def get_current_pharmacist_info(
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Получение информации о текущем фармацевте"""
    return PharmacistResponse(
        uuid=pharmacist.uuid,
        user=UserResponse.model_validate(pharmacist.user),
        pharmacy_info=pharmacist.pharmacy_info,  # ✅ Используем JSON данные
        is_active=pharmacist.is_active,
    )


# Новые эндпоинты для управления онлайн статусом
@router.post("/online")
async def set_online(
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Перевести фармацевта в онлайн"""
    pharmacist.is_online = True
    pharmacist.last_seen = get_utc_now_naive()
    await db.commit()

    return {"status": "success", "message": "Вы теперь онлайн"}


@router.post("/offline")
async def set_offline(
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Перевести фармацевта в офлайн"""
    pharmacist.is_online = False
    pharmacist.last_seen = get_utc_now_naive()
    await db.commit()

    return {"status": "success", "message": "Вы теперь офлайн"}


@router.get("/status")
async def get_status(pharmacist: Pharmacist = Depends(get_current_pharmacist)):
    """Получить текущий статус фармацевта"""
    return {
        "is_online": pharmacist.is_online,
        "last_seen": pharmacist.last_seen,
        "is_active": pharmacist.is_active,
        "pharmacy_info": pharmacist.pharmacy_info,
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/refresh/", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Получить новый access token по refresh token"""
    # Валидируем refresh token
    token_data = await validate_refresh_token(request.refresh_token, db)

    # Создаём новый access token
    new_access_token = create_access_token(
        data={"sub": token_data["user_id"], "type": "access"}
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


@router.post("/logout/")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Выход — отзыв refresh token"""
    await revoke_refresh_token(request.refresh_token, db)

    # Переводим фармацевта в офлайн
    pharmacist.is_online = False
    pharmacist.last_seen = get_utc_now_naive()
    await db.commit()

    return {"status": "success", "message": "Logged out successfully"}


# В конце pharmacist_auth.py добавить:
__all__ = [
    "router",
    "get_pharmacist_by_telegram_id",
    "get_or_create_user",
    "register_pharmacist",
    "pharmacist_login",
]
