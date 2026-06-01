from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
import uuid
import logging
import os
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from db.database import get_db
from db.qa_models import User
from db.token_models import RefreshToken
from utils.time_utils import get_utc_now_naive
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserRegisterRequest(BaseModel):
    """Модель запроса для регистрации пользователя"""

    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    consent_privacy_policy: bool = True
    consent_transboundary_transfer: bool = False


class UserLoginRequest(BaseModel):
    """Модель запроса для входа пользователя"""

    email: Optional[str] = None
    phone: Optional[str] = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    uuid: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = get_utc_now_naive() + expires_delta
    else:
        expire = get_utc_now_naive() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = get_utc_now_naive() + expires_delta
    else:
        expire = get_utc_now_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_email_or_phone(
    email: Optional[str], phone: Optional[str], db: AsyncSession
) -> Optional[User]:
    """Find user by email or phone"""
    query = select(User)

    if email:
        # Note: In production, you should use encrypted fields
        query = query.where(User.email_encrypted == email)
    elif phone:
        query = query.where(User.phone_encrypted == phone)
    else:
        return None

    result = await db.execute(query)
    return result.scalar_one_or_none()


@router.post("/register/", response_model=UserResponse)
@limiter.limit("5/minute")
async def register_user(
    request: Request,
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация нового пользователя (rate limit 5/min)"""
    try:
        # Check if user already exists
        existing_user = await get_user_by_email_or_phone(
            user_data.email, user_data.phone, db
        )
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким email или телефоном уже существует",
            )

        # Validate that at least email or phone is provided
        if not user_data.email and not user_data.phone:
            raise HTTPException(
                status_code=400, detail="Необходимо указать email или телефон"
            )

        # Hash password
        hashed_password = pwd_context.hash(user_data.password)

        # Create new user
        new_user = User(
            uuid=uuid.uuid4(),
            email_encrypted=user_data.email,
            phone_encrypted=user_data.phone,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            user_type="customer",
            consent_privacy_policy=user_data.consent_privacy_policy,
            consent_privacy_policy_date=(
                get_utc_now_naive() if user_data.consent_privacy_policy else None
            ),
            consent_transboundary_transfer=user_data.consent_transboundary_transfer,
            consent_transboundary_transfer_date=(
                get_utc_now_naive()
                if user_data.consent_transboundary_transfer
                else None
            ),
            created_at=get_utc_now_naive(),
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"New user registered: {new_user.uuid}")

        return UserResponse.model_validate(new_user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("User registration failed")
        raise HTTPException(
            status_code=500, detail="Ошибка регистрации. Попробуйте позже."
        )


@router.post("/login/", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_user(
    request: Request,
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Вход пользователя по email/телефону и паролю (rate limit 10/min)"""
    try:
        # Find user
        user = await get_user_by_email_or_phone(login_data.email, login_data.phone, db)

        if not user:
            raise HTTPException(
                status_code=401, detail="Неверный email/телефон или пароль"
            )

        # Verify password
        if not user.password_hash or not pwd_context.verify(
            login_data.password, user.password_hash
        ):
            raise HTTPException(
                status_code=401, detail="Неверный email/телефон или пароль"
            )

        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = create_access_token(
            data={"sub": str(user.uuid), "type": "access"},
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            data={"sub": str(user.uuid), "type": "refresh"},
            expires_delta=refresh_token_expires,
        )

        # Store refresh token in database
        new_refresh_token = RefreshToken(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            token=refresh_token,
            expires_at=get_utc_now_naive() + refresh_token_expires,
            is_active=True,
        )
        db.add(new_refresh_token)
        await db.commit()

        logger.info(f"User logged in: {user.uuid}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("User login failed")
        raise HTTPException(status_code=500, detail="Ошибка входа. Попробуйте позже.")


@router.post("/refresh/", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token_endpoint(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Обновление access токена (rate limit 20/min)"""
    try:
        # Decode refresh token
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if user_id is None or token_type != "refresh":
                raise HTTPException(status_code=401, detail="Неверный токен обновления")
        except JWTError:
            raise HTTPException(status_code=401, detail="Неверный токен обновления")

        # Check if refresh token exists and is active in database
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token,
                RefreshToken.is_active == True,
                RefreshToken.expires_at > get_utc_now_naive(),
            )
        )
        db_refresh_token = result.scalar_one_or_none()

        if not db_refresh_token:
            raise HTTPException(
                status_code=401, detail="Токен обновления недействителен или истек"
            )

        # Get user
        result = await db.execute(select(User).where(User.uuid == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        # Invalidate old refresh token
        db_refresh_token.is_active = False
        await db.commit()

        # Create new tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        new_access_token = create_access_token(
            data={"sub": str(user.uuid), "type": "access"},
            expires_delta=access_token_expires,
        )

        new_refresh_token_str = create_refresh_token(
            data={"sub": str(user.uuid), "type": "refresh"},
            expires_delta=refresh_token_expires,
        )

        # Store new refresh token
        new_refresh_token = RefreshToken(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            token=new_refresh_token_str,
            expires_at=get_utc_now_naive() + refresh_token_expires,
            is_active=True,
        )
        db.add(new_refresh_token)
        await db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Token refresh failed")
        raise HTTPException(status_code=500, detail="Ошибка обновления токена")


@router.post("/logout/")
async def logout_user(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Выход пользователя (инвалидация refresh токена)"""
    try:
        # Invalidate refresh token in database
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        db_refresh_token = result.scalar_one_or_none()

        if db_refresh_token:
            db_refresh_token.is_active = False
            await db.commit()
            logger.info(f"User logged out, token invalidated")

        return {"message": "Успешный выход"}

    except Exception as e:
        logger.exception("Logout failed")
        raise HTTPException(status_code=500, detail="Ошибка выхода")


@router.get("/me/", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Получить информацию о текущем пользователе"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Требуется авторизация")

        token = auth_header.split(" ")[1]

        # Decode token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if user_id is None or token_type != "access":
                raise HTTPException(status_code=401, detail="Неверный токен")
        except JWTError:
            raise HTTPException(status_code=401, detail="Неверный или истекший токен")

        # Get user
        result = await db.execute(select(User).where(User.uuid == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get current user")
        raise HTTPException(
            status_code=500, detail="Ошибка получения данных пользователя"
        )


@router.post("/login/telegram/", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_with_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Telegram WebApp login for users (via Authorization header with tma initData).
    Auto-creates user if not exists.
    """
    try:
        from aiogram.utils.web_app import safe_parse_webapp_init_data

        # Get initData from Authorization header (tma format)
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("tma "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. Expected: 'tma <initData>'",
            )

        init_data_str = auth_header[4:]  # Remove "tma " prefix

        # Validate initData using Telegram Bot API
        BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Bot token not configured")

        try:
            init_data = safe_parse_webapp_init_data(
                token=BOT_TOKEN, init_data=init_data_str
            )
        except Exception as e:
            logger.error(f"Invalid initData: {e}")
            raise HTTPException(status_code=401, detail="Invalid or tampered initData")

        if not init_data or not init_data.user:
            raise HTTPException(status_code=401, detail="No user data in initData")

        telegram_user = init_data.user
        telegram_id = telegram_user.id

        # Get or create user
        from services.user_service import get_or_create_user

        user = await get_or_create_user(
            db,
            telegram_id=telegram_id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            telegram_username=telegram_user.username,
            user_type="customer",  # Regular user, not pharmacist
        )

        logger.info(f"User logged in via Telegram: {user.uuid} (tg_id={telegram_id})")

        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = create_access_token(
            data={"sub": str(user.uuid), "type": "access"},
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            data={"sub": str(user.uuid), "type": "refresh"},
            expires_delta=refresh_token_expires,
        )

        # Store refresh token in database
        new_refresh_token = RefreshToken(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            token=refresh_token,
            expires_at=get_utc_now_naive() + refresh_token_expires,
            is_active=True,
        )
        db.add(new_refresh_token)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Telegram login failed")
        raise HTTPException(
            status_code=500, detail="Login failed. Please try again later."
        )


__all__ = ["router"]
