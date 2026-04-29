from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid
import logging
import os

from db.database import get_db
from db.qa_models import User, Pharmacist
from services.user_service import get_or_create_user
from db.qa_schemas import (
    PharmacistCreate,
    PharmacistResponse,
    UserResponse,
    PharmacyInfoSimple,
)
from auth.session_manager import create_session_token, delete_session
from auth.session_auth import get_current_pharmacist_session

from pydantic import BaseModel, Field
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)
router = APIRouter()


class PharmacistRegisterRequest(BaseModel):
    """Модель запроса для регистрации фармацевта"""
    telegram_user_id: int = Field(..., description="Telegram ID пользователя")
    first_name: Optional[str] = Field(None, description="Имя из Telegram")
    last_name: Optional[str] = Field(None, description="Фамилия из Telegram")
    telegram_username: Optional[str] = Field(None, description="Username из Telegram")
    pharmacy_info: Optional[dict] = Field(default_factory=dict, description="Информация об аптеке")


class PharmacistLoginRequest(BaseModel):
    """Модель запроса для логина фармацевта"""
    telegram_user_id: int = Field(..., description="Telegram ID пользователя")
    first_name: Optional[str] = Field(None, description="Имя из Telegram")
    last_name: Optional[str] = Field(None, description="Фамилия из Telegram")
    telegram_username: Optional[str] = Field(None, description="Username из Telegram")


class TelegramLoginRequest(BaseModel):
    """Модель запроса для валидации Telegram initData (пустая, так как данные передаются в заголовке)"""
    pass


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
    reg_data: PharmacistRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация фармацевта с проверкой дубликатов (rate limit 5/min)"""
    try:
        user = await get_or_create_user(
            db,
            telegram_id=reg_data.telegram_user_id,
            first_name=reg_data.first_name,
            last_name=reg_data.last_name,
            telegram_username=reg_data.telegram_username,
            user_type="pharmacist",
        )
        pharmacy_info = reg_data.pharmacy_info or {}

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
        logger.exception("Pharmacist registration failed")
        raise HTTPException(
            status_code=500, detail="Registration failed. Please try again later."
        )


@router.post("/login/")
@limiter.limit("10/minute")
async def pharmacist_login(
    request: Request,
    login_data: PharmacistLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Логин фармацевта по Telegram ID (возвращает session token)"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == login_data.telegram_user_id)
            .where(Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        if not pharmacists:
            raise HTTPException(status_code=404, detail="Фармацевт не найден")

        # Берем первого активного фармацевта
        pharmacist = pharmacists[0]
        
        # Обновляем данные пользователя из Telegram, если они предоставлены
        user = pharmacist.user
        updated_fields = []
        
        if login_data.first_name and user.first_name != login_data.first_name:
            user.first_name = login_data.first_name
            updated_fields.append("first_name")
            
        if login_data.last_name and user.last_name != login_data.last_name:
            user.last_name = login_data.last_name
            updated_fields.append("last_name")
            
        if login_data.telegram_username and user.telegram_username != login_data.telegram_username:
            user.telegram_username = login_data.telegram_username
            updated_fields.append("telegram_username")
        
        # Сохраняем изменения, если были обновления
        if updated_fields:
            logger.info(f"Updated user fields for telegram_id {login_data.telegram_user_id}: {updated_fields}")
            await db.commit()
            await db.refresh(user)

        # Обновляем статус онлайн и время последней активности
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()

        # Если нужно, можно вернуть список всех аптек для выбора
        if len(pharmacists) > 1:
            logger.info(
                f"User {login_data.telegram_user_id} has {len(pharmacists)} active pharmacist profiles"
            )

        # Создаём простой session token
        session_token = create_session_token(
            telegram_id=login_data.telegram_user_id,
            pharmacist_uuid=str(pharmacist.uuid),
            user_id=str(pharmacist.user_id)
        )

        return {
            "session_token": session_token,
            "token_type": "session",
            "expires_in": 86400,  # 24 часа
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
        logger.exception("Pharmacist login failed")
        raise HTTPException(
            status_code=500, detail="Login failed. Please try again later."
        )


@router.post("/login/telegram/")
async def telegram_webapp_login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Валидация Telegram WebApp initData и выдача session token
    
    Этот эндпоинт принимает rawData из заголовка Authorization: tma <initData>, 
    проверяет подпись и выдает простой session token для аутентификации фармацевта.
    """
    try:
        # Импортируем утилиту aiogram для валидации
        from aiogram.utils.web_app import safe_parse_webapp_init_data
        from sqlalchemy.exc import IntegrityError
        
        # Получаем initData из заголовка Authorization
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("tma "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Use 'tma <initData>'"
            )
        
        init_data_raw = auth_header[4:]  # убираем префикс "tma "
        
        # Получаем токен бота из окружения
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error"
            )
        
        # Валидируем initData подпись
        try:
            validated_data = safe_parse_webapp_init_data(
                token=bot_token,
                init_data=init_data_raw
            )
        except ValueError as e:
            logger.warning(f"Invalid initData signature: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid Telegram initData signature"
            )
        
        # Извлекаем информацию о пользователе
        if not validated_data.user:
            logger.warning("No user data in validated initData")
            raise HTTPException(
                status_code=401,
                detail="Invalid Telegram initData: no user data"
            )
            
        telegram_id = validated_data.user.id
        first_name = validated_data.user.first_name or ""
        last_name = validated_data.user.last_name or ""
        username = validated_data.user.username or ""
        
        logger.info(f"Telegram login attempt: telegram_id={telegram_id}, user={first_name} {last_name}")
        
        # Находим фармацевта по telegram_id
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == telegram_id)
            .where(Pharmacist.is_active == True)
        )
        pharmacist = result.scalar_one_or_none()
        
        if not pharmacist:
            logger.warning(f"Pharmacist not found for telegram_id={telegram_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Фармацевт не найден для Telegram ID {telegram_id}. Обратитесь к администратору."
            )
        
        # Обновляем данные пользователя из Telegram
        user = pharmacist.user
        updated_fields = []
        
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated_fields.append("first_name")
            
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated_fields.append("last_name")
            
        if username and user.telegram_username != username:
            user.telegram_username = username
            updated_fields.append("telegram_username")
        
        # Сохраняем изменения, если были обновления
        if updated_fields:
            logger.info(f"Updated user fields for telegram_id {telegram_id}: {updated_fields}")
            await db.commit()
            await db.refresh(user)
        
        # Обновляем статус онлайн и время последней активности
        pharmacist.is_online = True
        pharmacist.last_seen = get_utc_now_naive()
        await db.commit()
        
        # Создаём простой session token вместо JWT
        session_token = create_session_token(
            telegram_id=telegram_id,
            pharmacist_uuid=str(pharmacist.uuid),
            user_id=str(pharmacist.user_id)
        )
        
        logger.info(f"✅ Telegram login successful for pharmacist user_id={pharmacist.user_id}, pharmacist_uuid={pharmacist.uuid}")
        
        return {
            "session_token": session_token,
            "token_type": "session",
            "expires_in": 86400,  # 24 часа
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Telegram WebApp login failed")
        raise HTTPException(
            status_code=500,
            detail="Login failed. Please try again later."
        )


@router.get("/me", response_model=PharmacistResponse)
async def get_current_pharmacist_profile(
    pharmacist: Pharmacist = Depends(get_current_pharmacist_session),
):
    """
    Get current authenticated pharmacist profile
    
    This endpoint returns the profile of the currently authenticated pharmacist.
    It requires a valid session token in the Authorization header.
    """
    try:
        # Use model_validate to properly convert SQLAlchemy model to Pydantic model
        return PharmacistResponse.model_validate(pharmacist)
    except Exception as e:
        logger.exception("Failed to get pharmacist profile")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve pharmacist profile"
        )
