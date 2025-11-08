# routers/pharmacies.py
from fastapi import APIRouter, HTTPException, status
import csv
import uuid
from db.database import async_session_maker
from db.models import Pharmacy
from sqlalchemy import select

router = APIRouter()


@router.post("/load-pharmacies/")
async def load_pharmacies():
    """Эндпоинт для загрузки данных аптек из CSV"""
    try:
        csv_file_path = 'data/pharmacies_info.csv'

        async with async_session_maker() as session:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                pharmacies_loaded = 0
                pharmacies_updated = 0

                for row in reader:
                    # Проверяем существование аптеки
                    existing_pharmacy = await session.execute(
                        select(Pharmacy).where(
                            Pharmacy.pharmacy_number == row["pharmacy_number"]
                        )
                    )
                    existing_pharmacy = existing_pharmacy.scalar_one_or_none()

                    if existing_pharmacy:
                        # Обновляем
                        existing_pharmacy.name = row["name"]
                        existing_pharmacy.city = row["city"]
                        existing_pharmacy.address = row["address"]
                        existing_pharmacy.phone = row["phone"]
                        existing_pharmacy.opening_hours = row["opening_hours"]
                        pharmacies_updated += 1
                    else:
                        # Создаем новую
                        pharmacy = Pharmacy(
                            uuid=uuid.uuid4(),
                            name=row["name"],
                            pharmacy_number=row["pharmacy_number"],
                            city=row["city"],
                            address=row["address"],
                            phone=row["phone"],
                            opening_hours=row["opening_hours"],
                        )
                        session.add(pharmacy)
                        pharmacies_loaded += 1

                await session.commit()

                return {
                    "status": "success",
                    "message": "Данные аптек успешно загружены",
                    "loaded": pharmacies_loaded,
                    "updated": pharmacies_updated,
                    "total": pharmacies_loaded + pharmacies_updated,
                }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке данных аптек: {str(e)}",
        )


@router.get("/pharmacies/")
async def get_pharmacies():
    """Получить список всех аптек"""
    async with async_session_maker() as session:
        result = await session.execute(select(Pharmacy))
        pharmacies = result.scalars().all()
        return pharmacies
