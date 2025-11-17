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

# В pharmacist_auth.py в функции register_pharmacist
@router.post("/register-from-telegram/", response_model=PharmacistResponse)
async def register_pharmacist(
    telegram_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация фармацевта с проверкой дубликатов"""
    try:
        user = await get_or_create_user(telegram_data, db)
        pharmacy_info = telegram_data.get("pharmacy_info", {})

        # Проверяем, нет ли уже такой же записи
        result = await db.execute(
            select(Pharmacist)
            .where(Pharmacist.user_id == user.uuid)
            .where(Pharmacist.pharmacy_info["name"].astext == pharmacy_info.get("name"))
        )
        existing_pharmacist = result.scalar_one_or_none()

        if existing_pharmacist:
            # Если запись уже есть, активируем ее
            existing_pharmacist.is_active = True
            pharmacist = existing_pharmacist
        else:
            # Создаем новую запись
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

        # Если нужно, можно вернуть список всех аптек для выбора
        if len(pharmacists) > 1:
            logger.info(f"User {telegram_user_id} has {len(pharmacists)} active pharmacist profiles")

        # Создаем JWT токен
        access_token = create_access_token(data={"sub": str(pharmacist.uuid)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "pharmacist": PharmacistResponse(
                uuid=pharmacist.uuid,
                user=UserResponse.model_validate(pharmacist.user),
                pharmacy_info=pharmacist.pharmacy_info,
                is_active=pharmacist.is_active
            ),
            "total_pharmacies": len(pharmacists)  # Информация о количестве аптек
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
