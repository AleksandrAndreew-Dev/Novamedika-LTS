from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid

from db.database import get_db
from db.qa_models import User, Pharmacist


from db.qa_schemas import PharmacistCreate, PharmacistResponse, UserResponse, PharmacyInfoSimple
from auth.auth import create_access_token, get_current_pharmacist
from utils.time_utils import get_utc_now_naive

router = APIRouter()

# pharmacist_auth.py - ДОБАВИТЬ эту функцию
async def get_or_create_user(telegram_data: dict, db: AsyncSession) -> User:
    """Найти или создать пользователя"""
    from sqlalchemy import select
    import uuid

    result = await db.execute(
        select(User).where(User.telegram_id == telegram_data["telegram_user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_data["telegram_user_id"],
            first_name=telegram_data.get("first_name"),
            last_name=telegram_data.get("last_name"),
            telegram_username=telegram_data.get("telegram_username"),
            user_type="pharmacist"
        )
        db.add(user)
        await db.flush()

    return user

@router.post("/register-from-telegram/", response_model=PharmacistResponse)
async def register_pharmacist(
    telegram_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация фармацевта с обновленной структурой данных"""
    try:
        user = await get_or_create_user(telegram_data, db)

        # Используем готовые данные об аптеке из telegram_data
        pharmacy_info = telegram_data.get("pharmacy_info", {})

        # Создаем фармацевта
        pharmacist = Pharmacist(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            pharmacy_info=pharmacy_info,
            is_active=True
        )

        db.add(pharmacist)
        await db.commit()
        await db.refresh(pharmacist)

        return PharmacistResponse(
            uuid=pharmacist.uuid,
            user=UserResponse.model_validate(user),
            pharmacy_info=PharmacyInfoSimple(**pharmacy_info),
            is_active=pharmacist.is_active
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/")
async def pharmacist_login(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Логин фармацевта по Telegram ID"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == telegram_user_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist:
            raise HTTPException(status_code=404, detail="Фармацевт не найден")

        # Создаем JWT токен
        access_token = create_access_token(data={"sub": str(pharmacist.uuid)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "pharmacist": PharmacistResponse(
                uuid=pharmacist.uuid,
                user=UserResponse.model_validate(pharmacist.user),
                pharmacy_info=pharmacist.pharmacy_info,  # ✅ Используем JSON данные
                is_active=pharmacist.is_active
            )
        }

@router.get("/me", response_model=PharmacistResponse)
async def get_current_pharmacist_info(
    pharmacist: Pharmacist = Depends(get_current_pharmacist)
):
    """Получение информации о текущем фармацевте"""
    return PharmacistResponse(
        uuid=pharmacist.uuid,
        user=UserResponse.model_validate(pharmacist.user),
        pharmacy_info=pharmacist.pharmacy_info,  # ✅ Используем JSON данные
        is_active=pharmacist.is_active
    )
