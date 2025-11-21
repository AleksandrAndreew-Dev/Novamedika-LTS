from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Pharmacy, Product

router = APIRouter()

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


@router.get("/search-two-step/", response_model=dict)
async def search_two_step(
    name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if not name:
        raise HTTPException(
            status_code=400, detail="Параметр 'name' обязателен для поиска"
        )

    _clean_old_contexts()

    # Разбиваем поисковый запрос на отдельные слова
    search_terms = name.strip().split()

    # Создаем условия для поиска по каждому слову
    name_conditions = []
    for term in search_terms:
        if len(term) > 2:  # Игнорируем слишком короткие слова
            name_conditions.append(Product.name.ilike(f"%{term}%"))

    # Если после фильтрации не осталось условий, используем оригинальный запрос
    if not name_conditions:
        name_conditions.append(Product.name.ilike(f"%{name}%"))

    # Базовый запрос с комбинированными условиями
    base_query = (
        select(Product)
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(or_(*name_conditions))
    )

    if city and city != "Все города" and city.strip():
        base_query = base_query.where(Pharmacy.city == city)

    # Запрос для получения форм с правильной фильтрацией
    forms_query = (
        select(Product.form, func.count(Product.uuid))
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(or_(*name_conditions))
    )

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

    # Превью товаров с сортировкой по релевантности и цене
    preview_query = (
        base_query.options(joinedload(Product.pharmacy))
        .order_by(Product.price.asc())
        .limit(20)  # Увеличиваем лимит для лучшего покрытия
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
                "country": product.country,
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
        "search_terms": search_terms,  # Сохраняем термины для поиска
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
    name: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    manufacturer: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    _clean_old_contexts()

    # Определяем параметры поиска
    search_name = name
    search_city = city
    search_terms = []

    if search_id and search_id in _search_context:
        context = _search_context[search_id]
        if not search_name:
            search_name = context["name"]
        # Используем сохраненные поисковые термины для более точного поиска
        search_terms = context.get("search_terms", [search_name])
        if not search_city:
            search_city = context["city"]

    # Если search_terms пуст, создаем из search_name
    if not search_terms and search_name:
        search_terms = search_name.strip().split()

    # Базовый запрос
    query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
    )

    # Улучшенная фильтрация по названию
    if search_terms:
        name_conditions = []
        for term in search_terms:
            if len(term) > 2:
                name_conditions.append(Product.name.ilike(f"%{term}%"))

        if name_conditions:
            query = query.where(or_(*name_conditions))
        elif search_name:
            query = query.where(Product.name.ilike(f"%{search_name}%"))

    if search_city and search_city != "Все города":
        query = query.where(Pharmacy.city.ilike(f"%{search_city}%"))
    if form:
        query = query.where(Product.form == form)
    if manufacturer:
        query = query.where(Product.manufacturer == manufacturer)
    if country:
        query = query.where(Product.country == country)

    # Сортировка по цене (от меньшей к большей)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    total_pages = ceil(total / size) if total > 0 else 1
    if page > total_pages:
        page = total_pages

    query = (
        query.order_by(Product.price.asc())
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await db.execute(query)
    products = result.unique().scalars().all()

    items = []
    for product in products:
        pharmacy = product.pharmacy
        items.append({
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
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "filters": {
            "name": search_name,
            "city": search_city,
            "form": form,
            "manufacturer": manufacturer,
            "country": country
        },
        "search_id": search_id,
    }


# Добавляем эндпоинт для триграммного поиска (опционально)
@router.get("/search-trigram/", response_model=dict)
async def search_trigram(
    name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    similarity: float = Query(0.3, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Поиск с использованием триграмм PostgreSQL
    Требует расширение: CREATE EXTENSION pg_trgm;
    """
    if not name:
        raise HTTPException(status_code=400, detail="Параметр 'name' обязателен")

    # Используем триграммное сходство
    trigram_query = text("""
        SELECT p.*, ph.*,
        similarity(p.name, :name) as similarity_score
        FROM products p
        JOIN pharmacies ph ON p.pharmacy_id = ph.uuid
        WHERE similarity(p.name, :name) > :similarity
        AND (:city IS NULL OR ph.city = :city)
        ORDER BY similarity_score DESC, p.price ASC
        LIMIT 100
    """)

    result = await db.execute(
        trigram_query,
        {"name": name, "city": city, "similarity": similarity}
    )
    products_data = result.fetchall()

    # Обработка результатов...
    # [аналогично предыдущим эндпоинтам]

    return {"items": [], "total": len(products_data)}  # Заглушка


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
