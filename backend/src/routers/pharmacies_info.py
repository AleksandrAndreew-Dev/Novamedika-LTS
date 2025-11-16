# routers/pharmacies_info.py
from fastapi import APIRouter, HTTPException, status, Depends
import csv
import uuid
from pathlib import Path
import re

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from db.database import async_session_maker
from db.models import Pharmacy
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Pharmacy, Product

router = APIRouter()

def parse_pharmacy_name(full_name: str) -> tuple[str, str, str]:
    """Разбирает полное название аптеки на название, номер и сеть"""
    # Паттерны для извлечения номера
    patterns = [
        r"^(.*?)\s*№\s*(\d+)$",  # "Новамедика №1"
        r"^(.*?)\s*#\s*(\d+)$",  # "Новамедика #1"
        r"^(.+?)\s+(\d+)$",  # "Новамедика 1"
    ]

    for pattern in patterns:
        match = re.match(pattern, full_name.strip())
        if match:
            name = match.group(1).strip()
            number = match.group(2).strip()

            # Определяем сеть по названию
            chain = determine_chain(name)

            return name, number, chain

    # Если не удалось разобрать, возвращаем как есть и определяем сеть
    chain = determine_chain(full_name.strip())
    return full_name.strip(), "", chain

def determine_chain(pharmacy_name: str) -> str:
    """Определяет сеть аптеки по названию"""
    name_lower = pharmacy_name.lower()

    if "новамедик" in name_lower or "novamedik" in name_lower:
        return "Новамедика"
    elif "эклини" in name_lower or "eklini" in name_lower:
        return "Эклиния"
    else:
        # По умолчанию или можно добавить логику для определения по другим признакам
        return "Новамедика"

@router.post("/load-pharmacies/")
async def load_pharmacies():
    """Эндпоинт для загрузки данных аптек из CSV"""
    try:
        base_dir = Path(__file__).resolve().parent.parent
        csv_file_path = base_dir / "data" / "pharmacies_info.csv"

        async with async_session_maker() as session:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                pharmacies_loaded = 0
                pharmacies_updated = 0
                errors = []

                for row_num, row in enumerate(reader, 1):
                    try:
                        full_name = row["name"]
                        pharmacy_name, pharmacy_number, chain = parse_pharmacy_name(full_name)

                        if not pharmacy_number:
                            pharmacy_number = row.get("pharmacy_number", "")

                        # Ищем аптеку по имени и номеру (уникальная комбинация)
                        existing_pharmacy = await session.execute(
                            select(Pharmacy).where(
                                and_(
                                    Pharmacy.name == pharmacy_name,
                                    Pharmacy.pharmacy_number == pharmacy_number,
                                )
                            )
                        )
                        existing_pharmacy = existing_pharmacy.scalar_one_or_none()

                        if existing_pharmacy:
                            # Обновляем только если данные изменились
                            update_needed = False
                            if existing_pharmacy.city != row["city"]:
                                existing_pharmacy.city = row["city"]
                                update_needed = True
                            if existing_pharmacy.address != row["address"]:
                                existing_pharmacy.address = row["address"]
                                update_needed = True
                            if existing_pharmacy.phone != row["phone"]:
                                existing_pharmacy.phone = row["phone"]
                                update_needed = True
                            if existing_pharmacy.opening_hours != row["opening_hours"]:
                                existing_pharmacy.opening_hours = row["opening_hours"]
                                update_needed = True
                            # Обновляем сеть, если она изменилась
                            if existing_pharmacy.chain != chain:
                                existing_pharmacy.chain = chain
                                update_needed = True

                            if update_needed:
                                pharmacies_updated += 1
                        else:
                            # Создаем новую аптеку
                            pharmacy = Pharmacy(
                                uuid=uuid.uuid4(),
                                name=pharmacy_name,
                                pharmacy_number=pharmacy_number,
                                city=row["city"],
                                address=row["address"],
                                phone=row["phone"],
                                opening_hours=row["opening_hours"],
                                chain=chain  # Используем определенную сеть
                            )
                            session.add(pharmacy)
                            pharmacies_loaded += 1

                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        continue

                await session.commit()

                return {
                    "status": "success",
                    "message": "Данные аптек успешно загружены",
                    "loaded": pharmacies_loaded,
                    "updated": pharmacies_updated,
                    "errors": errors,
                    "total": pharmacies_loaded + pharmacies_updated,
                }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке данных аптек: {str(e)}",
        )

# Остальные endpoints остаются без изменений
@router.get("/pharmacies/")
async def get_pharmacies():
    """Получить список всех аптек"""
    async with async_session_maker() as session:
        result = await session.execute(select(Pharmacy))
        pharmacies = result.scalars().all()
        return pharmacies

@router.get("/check-data/")
async def check_data(db: AsyncSession = Depends(get_db)):
    """Проверка загруженных данных"""
    # Проверяем аптеки
    pharmacies_result = await db.execute(select(Pharmacy))
    pharmacies = pharmacies_result.scalars().all()

    # Проверяем продукты
    products_result = await db.execute(
        select(Product).options(joinedload(Product.pharmacy)).limit(5)
    )
    sample_products = products_result.unique().scalars().all()

    sample_data = []
    for product in sample_products:
        sample_data.append(
            {
                "product_name": product.name,
                "pharmacy_name": (
                    product.pharmacy.name if product.pharmacy else "NO PHARMACY"
                ),
                "pharmacy_city": (
                    product.pharmacy.city if product.pharmacy else "NO CITY"
                ),
                "pharmacy_number": (
                    product.pharmacy.pharmacy_number
                    if product.pharmacy
                    else "NO NUMBER"
                ),
                "pharmacy_chain": (
                    product.pharmacy.chain if product.pharmacy else "NO CHAIN"
                ),
            }
        )

    return {
        "total_pharmacies": len(pharmacies),
        "sample_pharmacies": [
            {
                "name": p.name,
                "pharmacy_number": p.pharmacy_number,
                "city": p.city,
                "chain": p.chain
            }
            for p in pharmacies[:5]
        ],
        "sample_products": sample_data,
    }

from sqlalchemy import text

@router.delete("/clear-all-data/")
async def clear_all_data(db: AsyncSession = Depends(get_db)):
    """Очистка всех данных (продукты и аптеки)"""
    try:
        # Отключаем проверку внешних ключей для PostgreSQL
        await db.execute(text("SET session_replication_role = 'replica';"))

        # Удаляем все продукты
        await db.execute(text("DELETE FROM products;"))
        # Удаляем все аптеки
        await db.execute(text("DELETE FROM pharmacies;"))

        # Включаем проверку внешних ключей обратно
        await db.execute(text("SET session_replication_role = 'origin';"))

        await db.commit()

        return {"status": "success", "message": "Все данные успешно удалены"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении данных: {str(e)}",
        )
