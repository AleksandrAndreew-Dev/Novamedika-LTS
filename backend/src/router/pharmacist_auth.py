from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import uuid

from db.database import get_db
from db.qa_models import User, Pharmacist
from db.models import Pharmacy
from db.qa_schemas import PharmacistCreate, PharmacistResponse, UserResponse
from db.schemas import PharmacyRead
from auth.auth import create_access_token, get_current_pharmacist

router = APIRouter(prefix="/pharmacists", tags=["Pharmacists"])

@router.post("/register/", response_model=PharmacistResponse)
async def register_pharmacist(
    pharmacist_data: PharmacistCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Проверяем существование пользователя Telegram
        user_result = await db.execute(
            select(User).where(User.telegram_id == pharmacist_data.telegram_user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь Telegram не найден"
            )

        # Проверяем существование аптеки
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == pharmacist_data.pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Аптека не найдена"
            )

        # Проверяем, не зарегистрирован ли уже фармацевт
        existing_pharmacist_result = await db.execute(
            select(Pharmacist).where(
                and_(
                    Pharmacist.user_id == user.uuid,
                    Pharmacist.pharmacy_id == pharmacist_data.pharmacy_id
                )
            )
        )
        existing_pharmacist = existing_pharmacist_result.scalar_one_or_none()

        if existing_pharmacist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Фармацевт уже зарегистрирован для этой аптеки"
            )

        # Создаем фармацевта
        pharmacist = Pharmacist(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            pharmacy_id=pharmacist_data.pharmacy_id,
            is_active=True
        )

        db.add(pharmacist)
        await db.commit()
        await db.refresh(pharmacist)

        # Загружаем связанные данные
        await db.refresh(user)
        await db.refresh(pharmacy)

        return PharmacistResponse(
            uuid=pharmacist.uuid,
            user=UserResponse(
                uuid=user.uuid,
                first_name=user.first_name,
                last_name=user.last_name,
                telegram_username=user.telegram_username
            ),
            pharmacy=PharmacyRead(
                uuid=pharmacy.uuid,
                name=pharmacy.name,
                pharmacy_number=pharmacy.pharmacy_number,
                city=pharmacy.city,
                address=pharmacy.address,
                phone=pharmacy.phone,
                opening_hours=pharmacy.opening_hours
            ),
            is_active=pharmacist.is_active
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при регистрации фармацевта: {str(e)}"
        )

@router.post("/login/")
async def pharmacist_login(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Логин фармацевта по Telegram ID"""
    try:
        # Находим пользователя и фармацевта
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user), selectinload(Pharmacist.pharmacy))
            .where(User.telegram_id == telegram_user_id)
        )
        pharmacist = result.scalar_one_or_none()

        if not pharmacist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фармацевт не найден"
            )

        if not pharmacist.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Аккаунт фармацевта деактивирован"
            )

        # Создаем JWT токен
        access_token = create_access_token(data={"sub": str(pharmacist.uuid)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "pharmacist": PharmacistResponse(
                uuid=pharmacist.uuid,
                user=UserResponse(
                    uuid=pharmacist.user.uuid,
                    first_name=pharmacist.user.first_name,
                    last_name=pharmacist.user.last_name,
                    telegram_username=pharmacist.user.telegram_username
                ),
                pharmacy=PharmacyRead(
                    uuid=pharmacist.pharmacy.uuid,
                    name=pharmacist.pharmacy.name,
                    pharmacy_number=pharmacist.pharmacy.pharmacy_number,
                    city=pharmacist.pharmacy.city,
                    address=pharmacist.pharmacy.address,
                    phone=pharmacist.pharmacy.phone,
                    opening_hours=pharmacist.pharmacy.opening_hours
                ),
                is_active=pharmacist.is_active
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при входе: {str(e)}"
        )

@router.get("/me", response_model=PharmacistResponse)
async def get_current_pharmacist_info(
    pharmacist: Pharmacist = Depends(get_current_pharmacist)
):
    """Получение информации о текущем фармацевте"""
    return PharmacistResponse(
        uuid=pharmacist.uuid,
        user=UserResponse(
            uuid=pharmacist.user.uuid,
            first_name=pharmacist.user.first_name,
            last_name=pharmacist.user.last_name,
            telegram_username=pharmacist.user.telegram_username
        ),
        pharmacy=PharmacyRead(
            uuid=pharmacist.pharmacy.uuid,
            name=pharmacist.pharmacy.name,
            pharmacy_number=pharmacist.pharmacy.pharmacy_number,
            city=pharmacist.pharmacy.city,
            address=pharmacist.pharmacy.address,
            phone=pharmacist.pharmacy.phone,
            opening_hours=pharmacist.pharmacy.opening_hours
        ),
        is_active=pharmacist.is_active
    )

@router.get("/pharmacy/{pharmacy_id}/pharmacists")
async def get_pharmacists_by_pharmacy(
    pharmacy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить всех фармацевтов для указанной аптеки"""
    try:
        result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user), selectinload(Pharmacist.pharmacy))
            .where(Pharmacist.pharmacy_id == pharmacy_id, Pharmacist.is_active == True)
        )
        pharmacists = result.scalars().all()

        return [
            PharmacistResponse(
                uuid=pharmacist.uuid,
                user=UserResponse(
                    uuid=pharmacist.user.uuid,
                    first_name=pharmacist.user.first_name,
                    last_name=pharmacist.user.last_name,
                    telegram_username=pharmacist.user.telegram_username
                ),
                pharmacy=PharmacyRead(
                    uuid=pharmacist.pharmacy.uuid,
                    name=pharmacist.pharmacy.name,
                    pharmacy_number=pharmacist.pharmacy.pharmacy_number,
                    city=pharmacist.pharmacy.city,
                    address=pharmacist.pharmacy.address,
                    phone=pharmacist.pharmacy.phone,
                    opening_hours=pharmacist.pharmacy.opening_hours
                ),
                is_active=pharmacist.is_active
            )
            for pharmacist in pharmacists
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении фармацевтов: {str(e)}"
        )
