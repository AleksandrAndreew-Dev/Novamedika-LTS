from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, text, case, and_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Pharmacy, Product

from sqlalchemy.dialects.postgresql import TSVECTOR

router = APIRouter()



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



@router.get("/search-fts/", response_model=dict)
async def search_full_text(
    q: str = Query(..., description="Поисковый запрос"),
    city: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    manufacturer: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    search_query = q.strip().lower()
    words = search_query.split()

    # Создаем полнотекстовый запрос
    fts_query_str = " & ".join([f"{word}:*" for word in words if len(word) > 1])
    if not fts_query_str:
        fts_query_str = f"{search_query}:*"

    ts_query = func.to_tsquery("russian_simple", fts_query_str)

    # Определяем триграммное сходство
    trigram_similarity = func.similarity(Product.name, search_query)

    # Создаем список для всех условий
    all_conditions_list = []

    # УРОВЕНЬ 1: ТОЧНЫЕ СОВПАДЕНИЯ (высший приоритет)
    exact_match_conditions = []
    exact_match_conditions.append(Product.name.ilike(f"{search_query}"))
    exact_match_conditions.append(Product.name.ilike(f"{search_query}%"))
    exact_match_conditions.append(Product.name.ilike(f" {search_query} "))
    exact_match_conditions.append(Product.name.ilike(f"{search_query} "))
    exact_match_conditions.append(Product.name.ilike(f" {search_query}"))
    exact_match_conditions.append(Product.name.ilike(f"% {search_query}"))
    exact_match_conditions.append(Product.name.ilike(f"{search_query} %"))

    if exact_match_conditions:
        all_conditions_list.append(or_(*exact_match_conditions))

    # УРОВЕНЬ 2: ПОЛНОТЕКСТОВЫЙ ПОИСК (средний приоритет)
    fts_conditions = []
    fts_conditions.append(
        func.to_tsvector("russian_simple", Product.name).op("@@")(ts_query)
    )

    if len(words) > 1:
        word_conditions = []
        for word in words:
            if len(word) >= 3:
                word_conditions.append(Product.name.ilike(f"%{word}%"))
        if word_conditions:
            fts_conditions.append(or_(*word_conditions))

    if fts_conditions:
        all_conditions_list.append(or_(*fts_conditions))

    # УРОВЕНЬ 3: НЕТОЧНЫЙ ПОИСК/ОПЕЧАТКИ (низкий приоритет)
    fuzzy_conditions = []
    fuzzy_conditions.append(trigram_similarity > 0.7)
    fuzzy_conditions.append(Product.name.ilike(f"{search_query}%"))
    fuzzy_conditions.append(Product.name.ilike(f" {search_query}%"))

    if len(search_query) >= 5:
        root_length = min(5, len(search_query) - 1)
        search_root = search_query[:root_length]
        fuzzy_conditions.append(Product.name.ilike(f"{search_root}%"))
        fuzzy_conditions.append(Product.name.ilike(f"% {search_root}%"))

    if len(words) > 1:
        first_letters = "".join([word[0] for word in words if len(word) > 0])
        if len(first_letters) >= 3:
            fuzzy_conditions.append(Product.name.ilike(f"{first_letters}%"))

    if fuzzy_conditions:
        all_conditions_list.append(or_(*fuzzy_conditions))

    # Базовое условие: объединяем все уровни через OR
    if not all_conditions_list:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": size,
            "total_pages": 1,
            "available_combinations": [],
            "total_found": 0,
        }

    base_condition = or_(*all_conditions_list)

    # Продолжение функции остается без изменений...
    # Если форма выбрана, возвращаем пустой список комбинаций
    if form and form != "Все формы":
        available_combinations = []
        total_found = 0
    else:
        # Запрос для комбинаций с улучшенной сортировкой по приоритетам
        combinations_query = (
            select(
                Product.name,
                Product.form,
                Product.manufacturer,
                Product.country,
                func.count(Product.uuid).label("count"),
                func.min(Product.price).label("min_price"),
                func.max(Product.price).label("max_price"),
                func.count(Pharmacy.uuid.distinct()).label("pharmacy_count"),
                case((Product.name.ilike(f"{search_query}"), 100), else_=0).label("exact_score"),
                case((Product.name.ilike(f"{search_query}%"), 50), else_=0).label("starts_score"),
                case((Product.name.ilike(f"% {search_query} %"), 30), else_=0).label("word_score"),
                func.ts_rank(func.to_tsvector("russian_simple", Product.name), ts_query).label("fts_score"),
                trigram_similarity.label("trigram_score")
            )
            .join(Pharmacy)
            .where(base_condition)
        )

        if city and city != "Все города":
            combinations_query = combinations_query.where(Pharmacy.city == city)
        if min_price is not None:
            combinations_query = combinations_query.where(Product.price >= min_price)
        if max_price is not None:
            combinations_query = combinations_query.where(Product.price <= max_price)

        combinations_query = combinations_query.group_by(
            Product.name, Product.form, Product.manufacturer, Product.country
        ).order_by(
            text("""
                exact_score DESC,
                starts_score DESC,
                word_score DESC,
                fts_score DESC,
                trigram_score DESC,
                count DESC
            """),
            Product.name.asc()
        )

        combinations_result = await db.execute(combinations_query)
        combinations_data = combinations_result.all()

        available_combinations = [
            {
                "name": c.name,
                "form": c.form,
                "manufacturer": c.manufacturer,
                "country": c.country,
                "count": c.count,
                "min_price": float(c.min_price) if c.min_price else 0.0,
                "max_price": float(c.max_price) if c.max_price else 0.0,
                "pharmacy_count": c.pharmacy_count,
            } for c in combinations_data
        ]
        total_found = sum(c.count for c in combinations_data)

    # Основной запрос товаров с МНОГОУРОВНЕВОЙ СОРТИРОВКОЙ
    items_query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
        .where(base_condition)
    )

    # Применяем фильтры для товаров
    if city and city != "Все города":
        items_query = items_query.where(Pharmacy.city == city)
    if form and form != "Все формы":
        items_query = items_query.where(Product.form == form)
    if manufacturer and manufacturer != "Все производители":
        items_query = items_query.where(Product.manufacturer.ilike(f"%{manufacturer}%"))
    if country and country != "Все страны":
        items_query = items_query.where(Product.country.ilike(f"%{country}%"))
    if min_price is not None:
        items_query = items_query.where(Product.price >= min_price)
    if max_price is not None:
        items_query = items_query.where(Product.price <= max_price)

    # УЛУЧШЕННАЯ МНОГОУРОВНЕВАЯ СОРТИРОВКА:
    items_query = items_query.order_by(
        case(
            (Product.name.ilike(f"{search_query}"), 6),
            (Product.name.ilike(f"{search_query}%"), 5),
            (Product.name.ilike(f"% {search_query} %"), 4),
            (Product.name.ilike(f"% {search_query}"), 3),
            (Product.name.ilike(f"{search_query} %"), 2),
            else_=0
        ).desc(),
        func.ts_rank(func.to_tsvector("russian_simple", Product.name), ts_query).desc(),
        trigram_similarity.desc(),
        Product.price.asc()
    )

    # Пагинация
    count_query = select(func.count()).select_from(items_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_pages = ceil(total / size) if total > 0 else 1
    current_page = min(page, total_pages)

    items_result = await db.execute(
        items_query.offset((current_page - 1) * size).limit(size)
    )
    products = items_result.unique().scalars().all()

    # Форматирование результатов
    items = []
    for p in products:
        items.append({
            "uuid": str(p.uuid),
            "name": p.name,
            "form": p.form,
            "manufacturer": p.manufacturer,
            "country": p.country,
            "price": float(p.price) if p.price else 0.0,
            "quantity": float(p.quantity) if p.quantity else 0.0,
            "pharmacy_name": p.pharmacy.name if p.pharmacy else "Unknown",
            "pharmacy_city": p.pharmacy.city if p.pharmacy else "Unknown",
            "pharmacy_address": p.pharmacy.address if p.pharmacy else "Unknown",
            "pharmacy_phone": p.pharmacy.phone if p.pharmacy else "Unknown",
            "pharmacy_number": p.pharmacy.pharmacy_number if p.pharmacy else "N/A",
            "pharmacy_id": p.pharmacy.uuid if p.pharmacy else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "working_hours": getattr(p.pharmacy, 'working_hours', None) or
                           getattr(p.pharmacy, 'opening_hours', "9:00-21:00"),
        })

    return {
        "items": items,
        "total": total,
        "page": current_page,
        "size": size,
        "total_pages": total_pages,
        "available_combinations": available_combinations,
        "total_found": total_found,
    }
