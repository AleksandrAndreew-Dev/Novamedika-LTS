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

# ЗАМЕНИТЬ импорты
from db.qa_schemas import PharmacistCreate, PharmacistResponse, UserResponse, PharmacyInfoSimple
# УДАЛИТЬ: from db.models import Pharmacy
# УДАЛИТЬ: from db.schemas import PharmacyRead

@router.post("/register-from-telegram/", response_model=PharmacistResponse)
async def register_pharmacist(
    telegram_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация фармацевта с данными об аптеке в JSON"""
    try:
        user = await get_or_create_user(telegram_data, db)

        # Данные об аптеке (из Telegram)
        pharmacy_info = {
            "name": telegram_data.get("pharmacy_name", ""),
            "number": telegram_data.get("pharmacy_number", ""),
            "city": telegram_data.get("pharmacy_city", ""),
            "chain": telegram_data.get("pharmacy_chain", "Новамедика")
        }

        # Создаем фармацевта
        pharmacist = Pharmacist(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            pharmacy_info=pharmacy_info,  # ✅ Сохраняем в JSON
            is_active=True
        )

        db.add(pharmacist)
        await db.commit()
        await db.refresh(pharmacist)

        return PharmacistResponse(
            uuid=pharmacist.uuid,
            user=UserResponse.model_validate(user),
            pharmacy_info=pharmacy_info,
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
