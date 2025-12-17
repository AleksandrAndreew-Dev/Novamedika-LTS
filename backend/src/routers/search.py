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


# search.py - обновляем search-two-step для использования полнотекстового поиска
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

    # Нормализуем поисковый запрос
    search_name = name.strip()
    search_query = q.strip()

    # Полнотекстовый поиск
    ts_query = func.plainto_tsquery("russian_simple", search_query)

    # Базовый запрос с полнотекстовым поиском
    base_query = (
        select(Product)
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(Product.search_vector.op("@@")(ts_query))
    )

    if city and city != "Все города" and city.strip():
        base_query = base_query.where(Pharmacy.city == city)

    # Запрос для форм с релевантностью полнотекстового поиска
    forms_query = (
        select(
            Product.form,
            func.count(Product.uuid).label("count"),
            func.avg(func.ts_rank(Product.search_vector, ts_query)).label(
                "avg_relevance"
            ),
        )
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(Product.search_vector.op("@@")(ts_query))
    )

    if city and city != "Все города" and city.strip():
        forms_query = forms_query.where(Pharmacy.city == city)

    forms_query = forms_query.group_by(Product.form).order_by(
        text("avg_relevance DESC, count DESC, form")
    )

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

    available_forms = [form for form, count, relevance in forms_data if form]
    total_found = sum(count for form, count, relevance in forms_data)

    # Улучшенный превью с релевантностью полнотекстового поиска
    preview_query = (
        base_query.options(joinedload(Product.pharmacy))
        .order_by(
            func.ts_rank(Product.search_vector, ts_query).desc(),
            Product.price.asc(),
        )
        .limit(20)
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
                "relevance": (
                    "high"
                    if product.name.lower().find(search_name.lower()) != -1
                    else "medium"
                ),
            }
        )

    # Сохраняем нормализованный запрос
    search_id = str(uuid.uuid4())
    _search_context[search_id] = {
        "name": search_name,
        "city": city,
        "available_forms": available_forms,
        "search_terms": search_name.split(),
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

    if search_id and search_id in _search_context:
        context = _search_context[search_id]
        if not search_name:
            search_name = context["name"]
        if not search_city:
            search_city = context["city"]

    # Нормализуем поисковый запрос
    if search_name:
        search_name = search_name.strip().lower()

    # Базовый запрос
    query = select(Product).options(joinedload(Product.pharmacy)).join(Pharmacy)

    # Улучшенная фильтрация по названию
    if search_name:
        name_conditions = []

        # 1. Точное совпадение (высший приоритет)
        name_conditions.append(Product.name.ilike(f"{search_name}"))

        # 2. Совпадение с начала строки
        name_conditions.append(Product.name.ilike(f"{search_name}%"))

        # 3. Полное вхождение поисковой фразы
        name_conditions.append(Product.name.ilike(f"%{search_name}%"))

        # 4. Поиск по отдельным словам (только для слов длиной > 2 символов)
        search_terms = search_name.split()
        for term in search_terms:
            if len(term) > 2:
                name_conditions.append(Product.name.ilike(f"% {term} %"))
                name_conditions.append(Product.name.ilike(f"{term} %"))
                name_conditions.append(Product.name.ilike(f"% {term}"))

        # 5. Частичное совпадение для коротких слов
        if len(search_terms) > 0:
            first_term = search_terms[0]
            if len(first_term) >= 3:
                name_conditions.append(Product.name.ilike(f"{first_term[:3]}%"))

        if name_conditions:
            query = query.where(or_(*name_conditions))

    if search_city and search_city != "Все города":
        query = query.where(Pharmacy.city.ilike(f"%{search_city}%"))
    if form:
        query = query.where(Product.form == form)
    if manufacturer:
        query = query.where(Product.manufacturer.ilike(f"%{manufacturer}%"))
    if country:
        query = query.where(Product.country.ilike(f"%{country}%"))

    # Улучшенная сортировка с учетом релевантности
    if search_name:
        query = query.order_by(
            case((Product.name.ilike(f"%{search_name}%"), 1), else_=0).desc(),
            Product.price.asc(),
        )
    else:
        query = query.order_by(Product.price.asc())

    # Пагинация
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    total_pages = ceil(total / size) if total > 0 else 1
    if page > total_pages:
        page = total_pages

    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    products = result.unique().scalars().all()

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
        "filters": {
            "name": search_name,
            "city": search_city,
            "form": form,
            "manufacturer": manufacturer,
            "country": country,
        },
        "search_id": search_id,
    }


@router.get("/search-flexible/", response_model=dict)
async def search_flexible(
    name: str = Query(...),
    city: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Гибкий поиск с улучшенной релевантностью
    """
    search_terms = name.strip().lower().split()

    conditions = []

    # Построение сложных условий поиска
    for term in search_terms:
        if len(term) >= 3:
            # Для длинных слов ищем в разных позициях
            conditions.extend(
                [
                    Product.name.ilike(f"{term}%"),  # начало слова
                    Product.name.ilike(f"%{term}%"),  # любая позиция
                ]
            )
        else:
            # Для коротких слов - только точные вхождения
            conditions.extend(
                [
                    Product.name.ilike(f"% {term} %"),
                    Product.name.ilike(f"{term} %"),
                    Product.name.ilike(f"% {term}"),
                ]
            )

    query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
        .where(or_(*conditions))
    )

    if city and city != "Все города":
        query = query.where(Pharmacy.city == city)

    # Сложная сортировка по релевантности
    query = query.order_by(
        case((Product.name.ilike(f"%{name}%"), 3), else_=0).desc(), Product.price.asc()
    )

    # Пагинация и выполнение запроса
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    total_pages = ceil(total / size) if total > 0 else 1
    page = min(page, total_pages)

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    products = result.unique().scalars().all()

    # Форматирование результатов
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
    trigram_query = text(
        """
        SELECT p.*, ph.*,
        similarity(p.name, :name) as similarity_score
        FROM products p
        JOIN pharmacies ph ON p.pharmacy_id = ph.uuid
        WHERE similarity(p.name, :name) > :similarity
        AND (:city IS NULL OR ph.city = :city)
        ORDER BY similarity_score DESC, p.price ASC
        LIMIT 100
    """
    )

    result = await db.execute(
        trigram_query, {"name": name, "city": city, "similarity": similarity}
    )
    products_data = result.fetchall()

    # Обработка результатов...
    items = []
    for row in products_data:
        product_data = row._mapping
        items.append(
            {
                "uuid": str(product_data["uuid"]),
                "name": product_data["name"],
                "form": product_data["form"],
                "manufacturer": product_data["manufacturer"],
                "country": product_data["country"],
                "price": float(product_data["price"]) if product_data["price"] else 0.0,
                "quantity": (
                    float(product_data["quantity"]) if product_data["quantity"] else 0.0
                ),
                "pharmacy_name": (
                    product_data["name"] if product_data["name"] else "Unknown"
                ),
                "pharmacy_city": (
                    product_data["city"] if product_data["city"] else "Unknown"
                ),
                "pharmacy_address": (
                    product_data["address"] if product_data["address"] else "Unknown"
                ),
                "pharmacy_phone": (
                    product_data["phone"] if product_data["phone"] else "Unknown"
                ),
                "pharmacy_number": (
                    product_data["pharmacy_number"]
                    if product_data["pharmacy_number"]
                    else "N/A"
                ),
                "updated_at": (
                    product_data["updated_at"].isoformat()
                    if product_data["updated_at"]
                    else None
                ),
            }
        )

    return {"items": items, "total": len(items)}


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


@router.get("/search-advanced/", response_model=dict)
async def search_advanced(
    name: str = Query(...),
    city: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    manufacturer: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    use_fuzzy: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    search_name = name.strip().lower()
    search_terms = search_name.split()

    conditions = []

    # УЛУЧШЕННЫЕ УСЛОВИЯ ПОИСКА ДЛЯ ПОВЫШЕНИЯ ТОЧНОСТИ
    # 1. Точное совпадение (высший приоритет)
    conditions.append(Product.name.ilike(f"{search_name}"))

    # 2. Совпадение с начала строки
    conditions.append(Product.name.ilike(f"{search_name}%"))

    # 3. Полное вхождение поисковой фразы
    conditions.append(Product.name.ilike(f"%{search_name}%"))

    # 4. Поиск по отдельным словам (только для слов длиной > 2 символов)
    for term in search_terms:
        if len(term) > 2:
            conditions.append(Product.name.ilike(f"% {term} %"))
            conditions.append(Product.name.ilike(f"{term} %"))
            conditions.append(Product.name.ilike(f"% {term}"))

    # 5. Частичное совпадение для коротких слов
    if use_fuzzy and len(search_terms) > 0:
        first_term = search_terms[0]
        if len(first_term) >= 3:
            conditions.append(Product.name.ilike(f"{first_term[:3]}%"))

    # ОСНОВНОЙ ЗАПРОС ДЛЯ ГРУППИРОВКИ ПО КОМБИНАЦИЯМ (ВКЛЮЧАЯ НАЗВАНИЕ)
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
        )
        .join(Pharmacy)
        .where(or_(*conditions))
    )

    if city and city != "Все города":
        combinations_query = combinations_query.where(Pharmacy.city == city)

    combinations_query = combinations_query.group_by(
        Product.name, Product.form, Product.manufacturer, Product.country
    ).order_by(
        # ИЗМЕНЕННАЯ СОРТИРОВКА: сначала по названию, затем по форме
        Product.name.asc(),  # Сначала по названию препарата
        Product.form.asc(),  # Затем по форме
        Product.manufacturer.asc(),  # Затем по производителю
        Product.country.asc(),  # И по стране
    )

    combinations_result = await db.execute(combinations_query)
    combinations_data = combinations_result.all()

    # Формируем список уникальных комбинаций
    available_combinations = []
    for combo in combinations_data:
        if combo.form and combo.name:
            available_combinations.append(
                {
                    "name": combo.name,
                    "form": combo.form,
                    "manufacturer": combo.manufacturer,
                    "country": combo.country,
                    "count": combo.count,
                    "min_price": float(combo.min_price) if combo.min_price else 0.0,
                    "max_price": float(combo.max_price) if combo.max_price else 0.0,
                    "pharmacy_count": combo.pharmacy_count,
                }
            )

    # ЗАПРОС ДЛЯ ДЕТАЛЬНЫХ РЕЗУЛЬТАТОВ (при выборе комбинации)
    items = []
    total = 0
    total_pages = 1

    if form:  # Если выбрана конкретная комбинация
        query = (
            select(Product)
            .options(joinedload(Product.pharmacy))
            .join(Pharmacy)
            .where(or_(*conditions))
        )

        # Применяем фильтры выбранной комбинации
        if form and form != "Все формы":
            query = query.where(Product.form == form)
        if manufacturer and manufacturer != "Все производители":
            query = query.where(Product.manufacturer == manufacturer)
        if country and country != "Все страны":
            query = query.where(Product.country == country)
        if city and city != "Все города":
            query = query.where(Pharmacy.city == city)

        # Сортировка по цене
        query = query.order_by(Product.price.asc())

        # Пагинация
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        total_pages = ceil(total / size) if total > 0 else 1
        page = min(page, total_pages)

        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        products = result.unique().scalars().all()

        # Формируем результаты
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
        "available_combinations": available_combinations,
        "total_found": sum(combo["count"] for combo in available_combinations),
    }






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
    """
    Умный поиск: сначала точный FTS, при отсутствии результатов - поиск с опечатками
    """
    search_query = q.strip()
    use_fuzzy = False  # Флаг для отслеживания использования нечеткого поиска

    # Создаем TS_QUERY для полнотекстового поиска
    ts_query = func.plainto_tsquery("russian_simple", search_query)

    # БАЗОВЫЕ УСЛОВИЯ ПОИСКА
    base_conditions = []
    base_conditions.append(Product.search_vector.op("@@")(ts_query))

    # ФИЛЬТРЫ для основного запроса
    conditions_for_items = base_conditions.copy()

    if city and city != "Все города":
        conditions_for_items.append(Pharmacy.city == city)
    if form and form != "Все формы":
        conditions_for_items.append(Product.form == form)
    if manufacturer and manufacturer != "Все производители":
        conditions_for_items.append(Product.manufacturer.ilike(f"%{manufacturer}%"))
    if country and country != "Все страны":
        conditions_for_items.append(Product.country.ilike(f"%{country}%"))
    if min_price is not None:
        conditions_for_items.append(Product.price >= min_price)
    if max_price is not None:
        conditions_for_items.append(Product.price <= max_price)

    # УСЛОВИЯ ДЛЯ КОМБИНАЦИЙ (без фильтров формы/производителя/страны)
    conditions_for_combinations = base_conditions.copy()

    if city and city != "Все города":
        conditions_for_combinations.append(Pharmacy.city == city)
    if min_price is not None:
        conditions_for_combinations.append(Product.price >= min_price)
    if max_price is not None:
        conditions_for_combinations.append(Product.price <= max_price)

    # ЗАПРОС ДЛЯ КОМБИНАЦИЙ (первоначальный - точный поиск)
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
        )
        .join(Pharmacy)
        .where(and_(*conditions_for_combinations))
        .group_by(Product.name, Product.form, Product.manufacturer, Product.country)
        .order_by(Product.name.asc(), Product.form.asc())
    )

    combinations_result = await db.execute(combinations_query)
    combinations_data = combinations_result.all()

    # Если точный поиск не дал результатов, пробуем нечеткий поиск
    if not combinations_data:
        use_fuzzy = True

        # Условия для нечеткого поиска (триграммы)
        fuzzy_conditions = [
            func.similarity(Product.name, search_query) > 0.3,  # Порог для 1-2 опечаток
        ]

        # Заменяем условия для комбинаций на нечеткие
        conditions_for_combinations = fuzzy_conditions.copy()

        if city and city != "Все города":
            conditions_for_combinations.append(Pharmacy.city == city)
        if min_price is not None:
            conditions_for_combinations.append(Product.price >= min_price)
        if max_price is not None:
            conditions_for_combinations.append(Product.price <= max_price)

        # Пересчитываем комбинации с нечетким поиском
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
                func.avg(func.similarity(Product.name, search_query)).label(
                    "avg_similarity"
                ),
            )
            .join(Pharmacy)
            .where(and_(*conditions_for_combinations))
            .group_by(Product.name, Product.form, Product.manufacturer, Product.country)
            .order_by(text("avg_similarity DESC, count DESC"))
        )

        combinations_result = await db.execute(combinations_query)
        combinations_data = combinations_result.all()

        # Также заменяем условия для items на нечеткие
        conditions_for_items = fuzzy_conditions.copy()

        if city and city != "Все города":
            conditions_for_items.append(Pharmacy.city == city)
        if form and form != "Все формы":
            conditions_for_items.append(Product.form == form)
        if manufacturer and manufacturer != "Все производители":
            conditions_for_items.append(Product.manufacturer.ilike(f"%{manufacturer}%"))
        if country and country != "Все страны":
            conditions_for_items.append(Product.country.ilike(f"%{country}%"))
        if min_price is not None:
            conditions_for_items.append(Product.price >= min_price)
        if max_price is not None:
            conditions_for_items.append(Product.price <= max_price)

    # Формируем available_combinations
    available_combinations = []
    for combo in combinations_data:
        if combo.name:
            combo_dict = {
                "name": combo.name,
                "form": combo.form,
                "manufacturer": combo.manufacturer,
                "country": combo.country,
                "count": combo.count,
                "min_price": float(combo.min_price) if combo.min_price else 0.0,
                "max_price": float(combo.max_price) if combo.max_price else 0.0,
                "pharmacy_count": combo.pharmacy_count,
            }
            # Добавляем информацию о схожести для нечеткого поиска
            if use_fuzzy and hasattr(combo, "avg_similarity"):
                combo_dict["similarity_score"] = (
                    float(combo.avg_similarity) if combo.avg_similarity else 0.0
                )
            available_combinations.append(combo_dict)

    # ПАГИНАЦИЯ
    count_query = (
        select(func.count(Product.uuid))
        .join(Pharmacy)
        .where(and_(*conditions_for_items))
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    total_pages = ceil(total / size) if total > 0 else 1
    page = min(page, total_pages)

    # ОСНОВНОЙ ЗАПРОС с учетом типа поиска
    if use_fuzzy:
        # Нечеткий поиск - сортируем по схожести
        query = (
            select(
                Product,
                func.similarity(Product.name, search_query).label("similarity_score"),
            )
            .options(joinedload(Product.pharmacy))
            .join(Pharmacy)
            .where(and_(*conditions_for_items))
            .order_by(text("similarity_score DESC"), Product.price.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
    else:
        # Точный поиск - стандартная сортировка
        query = (
            select(Product)
            .options(joinedload(Product.pharmacy))
            .join(Pharmacy)
            .where(and_(*conditions_for_items))
            .order_by(
                case(
                    (Product.name.ilike(f"{search_query}"), 2),
                    (Product.name.ilike(f"{search_query}%"), 1),
                    else_=0,
                ).desc(),
                Product.price.asc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )

    result = await db.execute(query)

    if use_fuzzy:
        products_data = result.unique().all()
    else:
        products_data = result.unique().scalars().all()

    # ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТОВ
    items = []
    for row in products_data:
        if use_fuzzy:
            product = row[0]
            similarity_score = row[1]
        else:
            product = row
            similarity_score = 1.0  # Для точного поиска

        pharmacy = product.pharmacy

        # Определяем уровень релевантности
        relevance_level = (
            "high"
            if similarity_score > 0.7
            else "medium" if similarity_score > 0.4 else "low"
        )

        items.append(
            {
                "uuid": str(product.uuid),
                "name": product.name,
                "form": product.form,
                "manufacturer": product.manufacturer,
                "country": product.country,
                "price": float(product.price) if product.price else 0.0,
                "quantity": float(product.quantity) if product.quantity else 0.0,
                "relevance_score": float(similarity_score) if use_fuzzy else 1.0,
                "relevance_level": relevance_level,
                "search_type": "fuzzy" if use_fuzzy else "exact",
                "pharmacy_name": pharmacy.name if pharmacy else "Unknown",
                "pharmacy_city": pharmacy.city if pharmacy else "Unknown",
                "pharmacy_address": pharmacy.address if pharmacy else "Unknown",
                "pharmacy_phone": pharmacy.phone if pharmacy else "Unknown",
                "pharmacy_number": pharmacy.pharmacy_number if pharmacy else "N/A",
                "pharmacy_id": str(pharmacy.uuid) if pharmacy else None,
                "working_hours": (
                    pharmacy.opening_hours if pharmacy else "Уточняйте в аптеке"
                ),
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
        "available_combinations": available_combinations,
        "total_found": sum(combo["count"] for combo in available_combinations),
        "query": q,
        "search_metadata": {
            "used_fuzzy": use_fuzzy,
            "search_type": "fuzzy" if use_fuzzy else "exact",
            "message": (
                "Использован поиск с учетом опечаток" if use_fuzzy else "Точный поиск"
            ),
        },
        "filters": {
            "city": city,
            "form": form,
            "manufacturer": manufacturer,
            "country": country,
            "min_price": min_price,
            "max_price": max_price,
        },
    }
