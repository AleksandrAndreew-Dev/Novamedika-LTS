from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_, text, case, and_, literal
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Pharmacy, Product
from slowapi import Limiter
from slowapi.util import get_remote_address

from sqlalchemy.dialects.postgresql import TSVECTOR

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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


def calculate_max_distance(search_query: str) -> int:
    """Вычисляет максимальное расстояние Левенштейна в зависимости от длины запроса"""
    length = len(search_query)
    if length <= 3:
        return 1
    elif length <= 6:
        return 2
    elif length <= 10:
        return 3
    else:
        return 4


@router.get("/search-fts/", response_model=dict)
@limiter.limit("30/minute")
async def search_full_text(
    request: Request,
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

    # Вычисляем максимальное расстояние Левенштейна
    max_distance = calculate_max_distance(search_query)

    # Создаем полнотекстовый запрос
    fts_query_str = " & ".join([f"{word}:*" for word in words if len(word) > 1])
    if not fts_query_str:
        fts_query_str = f"{search_query}:*"

    ts_query = func.to_tsquery("russian_simple", fts_query_str)

    # Определяем триграммное сходство
    trigram_similarity = func.similarity(Product.name, search_query)

    # Определяем расстояние Левенштейна — вычисляется ОДИН РАЗ, переиспользуется в фильтрах и сортировке
    levenshtein_distance = func.levenshtein(func.lower(Product.name), search_query)
    levenshtein_normalized = case(
        (
            func.length(Product.name) > 0,
            1.0
            - (
                levenshtein_distance
                / func.greatest(func.length(Product.name), len(search_query))
            ),
        ),
        else_=0.0,
    )

    # Определяем условия для каждого уровня
    # УРОВЕНЬ 1: ТОЧНЫЕ СОВПАДЕНИЯ (высший приоритет)
    exact_conditions = []
    exact_conditions.append(Product.name.ilike(f"{search_query}"))
    exact_conditions.append(Product.name.ilike(f"{search_query}%"))
    exact_conditions.append(Product.name.ilike(f" {search_query} "))
    exact_conditions.append(Product.name.ilike(f"{search_query} "))
    exact_conditions.append(Product.name.ilike(f" {search_query}"))
    exact_conditions.append(Product.name.ilike(f"% {search_query}"))
    exact_conditions.append(Product.name.ilike(f"{search_query} %"))

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

    # УРОВЕНЬ 3: НЕТОЧНЫЙ ПОИСК/ОПЕЧАТКИ (низкий приоритет)
    # ПРЕДВАРИТЕЛЬНЫЙ ФИЛЬТР — дешёвые операции (ILIKE, trigram)
    fuzzy_pre_conditions = []
    fuzzy_pre_conditions.append(trigram_similarity > 0.3)  # Порог трigram-сходства
    fuzzy_pre_conditions.append(Product.name.ilike(f"{search_query}%"))
    fuzzy_pre_conditions.append(Product.name.ilike(f" {search_query}%"))

    if len(search_query) >= 5:
        root_length = min(5, len(search_query) - 1)
        search_root = search_query[:root_length]
        fuzzy_pre_conditions.append(Product.name.ilike(f"{search_root}%"))
        fuzzy_pre_conditions.append(Product.name.ilike(f"% {search_root}%"))

    if len(words) > 1:
        first_letters = "".join([word[0] for word in words if len(word) > 0])
        if len(first_letters) >= 3:
            fuzzy_pre_conditions.append(Product.name.ilike(f"{first_letters}%"))

    # ФИНАЛЬНЫЙ ФИЛЬТР — требует ПРЕДВАРИТЕЛЬНЫЙ ФИЛЬТР + Левенштейн
    fuzzy_final_condition = and_(
        or_(*fuzzy_pre_conditions),
        levenshtein_distance <= max_distance,
    )

    # Per-word Levenshtein — только если слов 2+, и только для слов >= 3 символов
    # Используем ILIKE предфильтр + Levenshtein (AND, не OR)
    word_lev_conditions = []
    for word in words:
        if len(word) >= 3:
            word_lev_conditions.append(
                and_(
                    Product.name.ilike(f"%{word}%"),
                    func.levenshtein(func.lower(Product.name), word) <= 2,
                )
            )

    fuzzy_condition = fuzzy_final_condition
    if word_lev_conditions:
        fuzzy_condition = or_(fuzzy_condition, or_(*word_lev_conditions))

    # Определяем список условий по уровням (в порядке приоритета)
    search_levels = [
        ("exact", exact_conditions),
        ("fts", fts_conditions),
        ("fuzzy", [fuzzy_condition]),
    ]

    # ОПТИМИЗАЦИЯ: вместо 3 отдельных COUNT-запросов — один запрос с CASE
    # Фильтруем None/пустые условия БЕЗ использования boolean evaluation SQLAlchemy clauses
    fts_conditions_list = [c for c in fts_conditions if c is not None]
    fts_clause = or_(*fts_conditions_list) if fts_conditions_list else literal(False)

    level_counts_query = (
        select(
            func.count(case((or_(*exact_conditions), 1), else_=None)).label(
                "exact_count"
            ),
            func.count(case((fts_clause, 1), else_=None)).label("fts_count"),
            func.count(case((fuzzy_condition, 1), else_=None)).label("fuzzy_count"),
        )
        .select_from(Product)
        .join(Pharmacy)
    )

    # Применяем фильтры к подсчёту уровней
    if city and city != "Все города":
        level_counts_query = level_counts_query.where(Pharmacy.city.ilike(city))
    if form and form != "Все формы":
        level_counts_query = level_counts_query.where(Product.form == form)
    if manufacturer and manufacturer != "Все производители":
        level_counts_query = level_counts_query.where(
            Product.manufacturer.ilike(f"%{manufacturer}%")
        )
    if country and country != "Все страны":
        level_counts_query = level_counts_query.where(
            Product.country.ilike(f"%{country}%")
        )
    if min_price is not None:
        level_counts_query = level_counts_query.where(Product.price >= min_price)
    if max_price is not None:
        level_counts_query = level_counts_query.where(Product.price <= max_price)

    level_counts_result = await db.execute(level_counts_query)
    row = level_counts_result.first()

    exact_count = row.exact_count if row else 0
    fts_count = row.fts_count if row else 0
    fuzzy_count = row.fuzzy_count if row else 0

    # Выбираем первый непустой уровень
    chosen_level_condition = None
    chosen_level_name = None

    level_map = [
        ("exact", exact_count, exact_conditions),
        ("fts", fts_count, fts_conditions),
        ("fuzzy", fuzzy_count, [fuzzy_condition]),
    ]

    for level_name, count, conditions in level_map:
        if count > 0 and conditions:
            chosen_level_condition = or_(*conditions)
            chosen_level_name = level_name
            break

    # Если ни один уровень не дал результатов, возвращаем пустой ответ
    if chosen_level_condition is None:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": size,
            "total_pages": 1,
            "available_combinations": [],
            "total_found": 0,
            "search_level": "none",
        }

    # Если form/manufacturer/country указаны (шаг 3 — конкретная комбинация),
    # ищем напрямую по фильтрам, без level-based поиска
    is_specific_combination = bool(form and manufacturer and country)

    if is_specific_combination:
        # Прямой поиск по фильтрам комбинации
        items_query = (
            select(Product).options(joinedload(Product.pharmacy)).join(Pharmacy)
        )

        if city and city != "Все города":
            items_query = items_query.where(Pharmacy.city.ilike(city))
        if form and form != "Все формы":
            items_query = items_query.where(Product.form == form)
        if manufacturer and manufacturer != "Все производители":
            items_query = items_query.where(
                Product.manufacturer.ilike(f"%{manufacturer}%")
            )
        if country and country != "Все страны":
            items_query = items_query.where(Product.country.ilike(f"%{country}%"))
        if min_price is not None:
            items_query = items_query.where(Product.price >= min_price)
        if max_price is not None:
            items_query = items_query.where(Product.price <= max_price)

        # Фильтруем только товары в наличии
        items_query = items_query.where(Product.quantity > 0)

        # Фильтр по имени: только ПЕРВОЕ значимое слово
        stopwords = {"уп", "упак", "н", "и", "в", "на", "по", "для", "от"}
        words = [w for w in search_query.split() if len(w) >= 2 and w not in stopwords]
        if words:
            items_query = items_query.where(Product.name.ilike(f"%{words[0]}%"))

        items_query = items_query.order_by(
            Product.price.asc(),
            Product.quantity.desc(),
        )

        count_query = select(func.count()).select_from(items_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        total_pages = ceil(total / size) if total > 0 else 1
        current_page = min(page, total_pages)

        items_result = await db.execute(
            items_query.offset((current_page - 1) * size).limit(size)
        )
        products = items_result.unique().scalars().all()

        items = []
        for p in products:
            items.append(
                {
                    "uuid": str(p.uuid),
                    "name": p.name,
                    "form": p.form,
                    "manufacturer": p.manufacturer,
                    "country": p.country,
                    "price": float(p.price) if p.price else 0.0,
                    "quantity": float(p.quantity) if p.quantity else 0.0,
                    "pharmacy_name": p.pharmacy.name if p.pharmacy else "Unknown",
                    "pharmacy_city": p.pharmacy.city if p.pharmacy else "Unknown",
                    "pharmacy_district": p.pharmacy.district if p.pharmacy else None,
                    "pharmacy_address": p.pharmacy.address if p.pharmacy else "Unknown",
                    "pharmacy_phone": p.pharmacy.phone if p.pharmacy else "Unknown",
                    "pharmacy_number": (
                        p.pharmacy.pharmacy_number if p.pharmacy else "N/A"
                    ),
                    "pharmacy_id": p.pharmacy.uuid if p.pharmacy else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    "working_hours": getattr(p.pharmacy, "working_hours", None)
                    or getattr(p.pharmacy, "opening_hours", "9:00-21:00"),
                }
            )

        return {
            "items": items,
            "total": total,
            "page": current_page,
            "size": size,
            "total_pages": total_pages,
            "available_combinations": [],
            "total_found": 0,
            "search_level": "specific_combination",
        }

    # Продолжение с выбранным условием...
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
                case((Product.name.ilike(f"{search_query}"), 100), else_=0).label(
                    "exact_score"
                ),
                case((Product.name.ilike(f"{search_query}%"), 50), else_=0).label(
                    "starts_score"
                ),
                case((Product.name.ilike(f"% {search_query} %"), 30), else_=0).label(
                    "word_score"
                ),
                func.ts_rank(
                    func.to_tsvector("russian_simple", Product.name), ts_query
                ).label("fts_score"),
                trigram_similarity.label("trigram_score"),
                levenshtein_normalized.label("levenshtein_score"),
            )
            .join(Pharmacy)
            .where(chosen_level_condition)
        )

        if city and city != "Все города":
            combinations_query = combinations_query.where(Pharmacy.city.ilike(city))
        if min_price is not None:
            combinations_query = combinations_query.where(Product.price >= min_price)
        if max_price is not None:
            combinations_query = combinations_query.where(Product.price <= max_price)

        combinations_query = (
            combinations_query.group_by(
                Product.name, Product.form, Product.manufacturer, Product.country
            )
            .having(func.sum(Product.quantity) > 0)
            .order_by(
                text(
                    """
                exact_score DESC,
                starts_score DESC,
                word_score DESC,
                fts_score DESC,
                trigram_score DESC,
                levenshtein_score DESC,
                count DESC
            """
                ),
                Product.name.asc(),
            )
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
            }
            for c in combinations_data
        ]
        total_found = sum(c.count for c in combinations_data)

    # Основной запрос товаров с МНОГОУРОВНЕВОЙ СОРТИРОВКОЙ
    items_query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
        .where(chosen_level_condition)
    )

    # Применяем фильтры для товаров
    if city and city != "Все города":
        items_query = items_query.where(Pharmacy.city.ilike(city))
    # Показываем только товары в наличии
    items_query = items_query.where(Product.quantity > 0)
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

    # УЛУЧШЕННАЯ МНОГОУРОВНЕВАЯ СОРТИРОВКА С ЛЕВЕНШТЕЙНОМ:
    items_query = items_query.order_by(
        case(
            (Product.name.ilike(f"{search_query}"), 6),
            (Product.name.ilike(f"{search_query}%"), 5),
            (Product.name.ilike(f"% {search_query} %"), 4),
            (Product.name.ilike(f"% {search_query}"), 3),
            (Product.name.ilike(f"{search_query} %"), 2),
            else_=0,
        ).desc(),
        func.ts_rank(func.to_tsvector("russian_simple", Product.name), ts_query).desc(),
        trigram_similarity.desc(),
        levenshtein_normalized.desc(),  # Добавляем нормализованное расстояние Левенштейна
        levenshtein_distance.asc(),  # И прямое расстояние (меньше = лучше)
        Product.price.asc(),
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
        items.append(
            {
                "uuid": str(p.uuid),
                "name": p.name,
                "form": p.form,
                "manufacturer": p.manufacturer,
                "country": p.country,
                "price": float(p.price) if p.price else 0.0,
                "quantity": float(p.quantity) if p.quantity else 0.0,
                "pharmacy_name": p.pharmacy.name if p.pharmacy else "Unknown",
                "pharmacy_city": p.pharmacy.city if p.pharmacy else "Unknown",
                "pharmacy_district": p.pharmacy.district if p.pharmacy else None,
                "pharmacy_address": p.pharmacy.address if p.pharmacy else "Unknown",
                "pharmacy_phone": p.pharmacy.phone if p.pharmacy else "Unknown",
                "pharmacy_number": p.pharmacy.pharmacy_number if p.pharmacy else "N/A",
                "pharmacy_id": p.pharmacy.uuid if p.pharmacy else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "working_hours": getattr(p.pharmacy, "working_hours", None)
                or getattr(p.pharmacy, "opening_hours", "9:00-21:00"),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": current_page,
        "size": size,
        "total_pages": total_pages,
        "available_combinations": available_combinations,
        "total_found": total_found,
        "search_level": chosen_level_name,  # Добавляем информацию об уровне поиска
    }
