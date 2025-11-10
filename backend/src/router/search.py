from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Pharmacy, Product

router = APIRouter(prefix="/api/search", tags=["search"])

_search_context = {}
TTL_MINUTES = 30


def _clean_old_contexts():
    """Очистка устаревших контекстов поиска"""
    now = datetime.now()
    expired_ids = []
    for search_id, context in _search_context.items():
        if now - context["created_at"] > timedelta(minutes=TTL_MINUTES):
            expired_ids.append(search_id)
    for search_id in expired_ids:
        del _search_context[search_id]


# search.py - улучшенная версия search-two-step
# search.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
@router.get("/search-two-step/", response_model=dict)
async def search_two_step(
    name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Первый этап поиска - только по названию и городу"""
    if not name:
        raise HTTPException(
            status_code=400, detail="Параметр 'name' обязателен для поиска"
        )

    _clean_old_contexts()

    # Базовый запрос с явным JOIN и правильной фильтрацией по городу
    base_query = (
        select(Product)
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(Product.name.ilike(f"%{name}%"))
    )

    # ИСПРАВЛЕНИЕ: Правильная фильтрация по городу
    if city and city != "Все города" and city.strip():
        base_query = base_query.where(
            Pharmacy.city == city
        )  # Используем точное сравнение вместо ilike

    # Запрос для получения форм с правильной фильтрацией
    forms_query = (
        select(Product.form, func.count(Product.uuid))
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(Product.name.ilike(f"%{name}%"))
    )

    # ИСПРАВЛЕНИЕ: Такая же фильтрация по городу в forms_query
    if city and city != "Все города" and city.strip():
        forms_query = forms_query.where(Pharmacy.city == city)

    forms_query = forms_query.group_by(Product.form).order_by(Product.form)

    forms_result = await db.execute(forms_query)
    forms_data = forms_result.all()

    if not forms_data:
        return {
            "available_forms": [],
            "preview_products": [],
            "total_found": 0,
            "filters": {"name": name, "city": city},
            "search_id": None,
            "message": "Товары не найдены",
        }

    available_forms = [form for form, count in forms_data if form]
    total_found = sum(count for form, count in forms_data)

    # Получаем превью с правильной фильтрацией
    preview_query = (
        base_query.options(joinedload(Product.pharmacy))
        .limit(10)
        .order_by(Product.updated_at.desc())
    )

    preview_result = await db.execute(preview_query)
    preview_products_data = preview_result.unique().scalars().all()

    preview_products = []
    for product in preview_products_data:
        preview_products.append(
            {
                "name": product.name,
                "form": product.form,
                "manufacturer": product.manufacturer,
                "price": float(product.price) if product.price else 0.0,
                "pharmacy_city": (
                    product.pharmacy.city if product.pharmacy else "Unknown"
                ),
            }
        )

    # Создаем контекст поиска
    search_id = str(uuid.uuid4())
    _search_context[search_id] = {
        "name": name,
        "city": city,
        "available_forms": available_forms,
        "created_at": datetime.now(),
    }

    return {
        "available_forms": available_forms,
        "preview_products": preview_products,
        "total_found": total_found,
        "filters": {"name": name, "city": city},
        "search_id": search_id,
    }


@router.get("/search/", response_model=dict)
async def search_products(
    search_id: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Второй этап поиска - с выбранной формой препарата
    """
    # Очищаем старые контексты
    _clean_old_contexts()

    # Определяем параметры поиска
    search_name = name
    search_city = city

    if search_id and search_id in _search_context:
        context = _search_context[search_id]
        search_name = context["name"]
        search_city = context["city"]

    # Базовый запрос с пагинацией
    query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
        .where(Product.name.ilike(f"%{search_name}%"))
    )

    if search_city and search_city != "Все города":
        query = query.where(Pharmacy.city.ilike(f"%{search_city}%"))
    if form:
        query = query.where(Product.form == form)

    # Получаем общее количество ДО пагинации
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Применяем пагинацию
    total_pages = ceil(total / size) if total > 0 else 1
    if page > total_pages:
        page = total_pages

    query = (
        query.order_by(Product.updated_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(query)
    products = result.unique().scalars().all()

    # Форматируем результаты
    items = []
    for product in products:
        pharmacy = product.pharmacy
        items.append(
            {
                "uuid": str(product.uuid),
                "name": product.name,
                "form": product.form,
                "manufacturer": product.manufacturer,
                "country": product.country,
                "price": float(product.price) if product.price else 0.0,
                "quantity": float(product.quantity) if product.quantity else 0.0,
                "pharmacy_name": pharmacy.name if pharmacy else "Unknown",
                "pharmacy_city": pharmacy.city if pharmacy else "Unknown",
                "pharmacy_address": pharmacy.address if pharmacy else "Unknown",
                "pharmacy_phone": pharmacy.phone if pharmacy else "Unknown",
                "pharmacy_number": pharmacy.pharmacy_number if pharmacy else "N/A",
                "updated_at": (
                    product.updated_at.isoformat() if product.updated_at else None
                ),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "filters": {"name": search_name, "city": search_city, "form": form},
        "search_id": search_id,
    }


# Остальные эндпоинты без изменений
@router.get("/cities/")
async def get_cities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pharmacy.city)
        .distinct()
        .order_by(Pharmacy.city)
        .where(Pharmacy.city.isnot(None))
    )
    cities = [row[0] for row in result.all() if row[0]]
    return cities


@router.get("/forms/")
async def get_forms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product.form)
        .distinct()
        .order_by(Product.form)
        .where(Product.form.isnot(None))
    )
    forms = [row[0] for row in result.all() if row[0]]
    return forms


# Добавьте в search.py
@router.get("/check-relations/")
async def check_relations(db: AsyncSession = Depends(get_db)):
    """Проверка связей между аптеками и продуктами"""

    # Проверяем количество записей
    pharmacies_count = await db.execute(select(func.count(Pharmacy.uuid)))
    products_count = await db.execute(select(func.count(Product.uuid)))

    # Проверяем продукты без аптек
    orphan_products = await db.execute(
        select(func.count(Product.uuid)).where(Product.pharmacy_id.is_(None))
    )

    # Проверяем аптеки без продуктов
    empty_pharmacies = await db.execute(
        select(func.count(Pharmacy.uuid)).where(~Pharmacy.products.any())
    )

    return {
        "pharmacies_count": pharmacies_count.scalar(),
        "products_count": products_count.scalar(),
        "orphan_products": orphan_products.scalar(),
        "empty_pharmacies": empty_pharmacies.scalar(),
    }
