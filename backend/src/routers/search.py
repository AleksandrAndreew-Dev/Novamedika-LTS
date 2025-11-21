from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, text, case
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

    # Нормализуем поисковый запрос
    search_name = name.strip().lower()

    # Улучшенный поиск: учитываем разные варианты
    name_conditions = []

    # 1. Полное совпадение (самый высокий приоритет)
    name_conditions.append(Product.name.ilike(f"%{search_name}%"))

    # 2. Разбиваем на слова и ищем каждое слово
    search_terms = search_name.split()

    for term in search_terms:
        term = term.strip()
        if term:
            # Для коротких слов (2 символа) ищем точное вхождение
            if len(term) <= 2:
                name_conditions.append(
                    or_(
                        Product.name.ilike(f"% {term} %"),  # слово отдельно
                        Product.name.ilike(f"{term} %"),  # слово в начале
                        Product.name.ilike(f"% {term}"),  # слово в конце
                        Product.name.ilike(f"%{term}%"),  # часть слова
                    )
                )
            else:
                # Для длинных слов ищем разные варианты
                name_conditions.append(Product.name.ilike(f"%{term}%"))

    # 3. Добавляем поиск по началу слова
    for term in search_terms:
        if len(term) >= 3:
            name_conditions.append(Product.name.ilike(f"{term}%"))

    # Базовый запрос
    base_query = (
        select(Product)
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(or_(*name_conditions))
    )

    if city and city != "Все города" and city.strip():
        base_query = base_query.where(Pharmacy.city == city)

    # Улучшенный запрос для форм с релевантностью
    forms_query = (
        select(
            Product.form,
            func.count(Product.uuid).label("count"),
            # Добавляем оценку релевантности
            func.max(
                case(
                    (
                        Product.name.ilike(f"%{search_name}%"),
                        3,
                    ),  # полное совпадение - высший приоритет
                    else_=1,
                )
            ).label("relevance"),
        )
        .join(Pharmacy, Product.pharmacy_id == Pharmacy.uuid)
        .where(or_(*name_conditions))
    )

    if city and city != "Все города" and city.strip():
        forms_query = forms_query.where(Pharmacy.city == city)

    forms_query = forms_query.group_by(Product.form).order_by(
        text("relevance DESC, count DESC, form")
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

    # Улучшенный превью с релевантностью
    preview_query = (
        base_query.options(joinedload(Product.pharmacy))
        .order_by(
            # Сначала товары с полным совпадением названия
            case((Product.name.ilike(f"%{search_name}%"), 1), else_=0).desc(),
            # Затем по цене
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
            }
        )

    # Сохраняем нормализованный запрос
    search_id = str(uuid.uuid4())
    _search_context[search_id] = {
        "name": search_name,  # сохраняем нормализованное имя
        "city": city,
        "available_forms": available_forms,
        "search_terms": search_terms,
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

        # 1. Полное совпадение
        name_conditions.append(Product.name.ilike(f"%{search_name}%"))

        # 2. По словам
        search_terms = search_name.split()
        for term in search_terms:
            term = term.strip()
            if term:
                if len(term) <= 2:
                    # Для коротких слов
                    name_conditions.append(
                        or_(
                            Product.name.ilike(f"% {term} %"),
                            Product.name.ilike(f"{term} %"),
                            Product.name.ilike(f"% {term}"),
                        )
                    )
                else:
                    name_conditions.append(Product.name.ilike(f"%{term}%"))

        # 3. По началу слов для длинных терминов
        for term in search_terms:
            if len(term) >= 3:
                name_conditions.append(Product.name.ilike(f"{term}%"))

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


# search.py - исправить эндпоинт search-advanced
@router.get("/search-advanced/", response_model=dict)
async def search_advanced(
    name: str = Query(...),
    city: Optional[str] = Query(None),
    use_fuzzy: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Расширенный поиск с поддержкой нечеткого соответствия
    """
    search_name = name.strip().lower()
    search_terms = search_name.split()

    conditions = []

    # Базовые условия
    conditions.append(Product.name.ilike(f"%{search_name}%"))

    # Поиск по отдельным словам
    for term in search_terms:
        if len(term) > 1:  # Игнорируем одиночные буквы
            conditions.append(Product.name.ilike(f"%{term}%"))

    # Дополнительные условия для нечеткого поиска
    if use_fuzzy and len(search_terms) > 0:
        first_term = search_terms[0]
        if len(first_term) >= 3:
            # Поиск с возможными опечатками (первые 3 символа должны совпадать)
            conditions.append(Product.name.ilike(f"{first_term[:3]}%"))

    query = (
        select(Product)
        .options(joinedload(Product.pharmacy))
        .join(Pharmacy)
        .where(or_(*conditions))
        .order_by(
            case(
                (Product.name.ilike(f"%{search_name}%"), 3),  # полное совпадение
                (Product.name.ilike(f"{search_name}%"), 2),  # начало с запроса
                else_=1,
            ).desc(),
            Product.price.asc(),
        )
    )

    if city and city != "Все города":
        query = query.where(Pharmacy.city == city)

    # Получаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    total_pages = ceil(total / size) if total > 0 else 1
    page = min(page, total_pages)

    # Получаем данные для пагинации
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    products = result.unique().scalars().all()

    # Получаем доступные формы для превью
    forms_query = (
        select(Product.form)
        .join(Pharmacy)
        .where(or_(*conditions))
        .group_by(Product.form)
        .order_by(Product.form)
    )

    if city and city != "Все города":
        forms_query = forms_query.where(Pharmacy.city == city)

    forms_result = await db.execute(forms_query)
    available_forms = [row[0] for row in forms_result.all() if row[0]]

    # Формируем превью продуктов (первые 20)
    preview_products = []
    preview_query = query.limit(20)
    preview_result = await db.execute(preview_query)
    preview_products_data = preview_result.unique().scalars().all()

    for product in preview_products_data:
        pharmacy = product.pharmacy
        preview_products.append(
            {
                "name": product.name,
                "form": product.form,
                "manufacturer": product.manufacturer,
                "country": product.country,
                "price": float(product.price) if product.price else 0.0,
                "pharmacy_city": pharmacy.city if pharmacy else "Unknown",
            }
        )

    # Формируем основные результаты
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
        "available_forms": available_forms,  # Добавляем доступные формы
        "preview_products": preview_products,  # Добавляем превью продуктов
        "total_found": total,  # Общее количество найденных
    }
