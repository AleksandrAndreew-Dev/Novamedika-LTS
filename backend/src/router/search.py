from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from math import ceil

from db.database import get_db
from db.models import Pharmacy, Product
from db.schemas import PharmacyRead, ProductRead

router = APIRouter(prefix="/api/search", tags=["search"])  # Добавляем префикс
# Временное хранилище для сохранения контекста поиска (в продакшене используйте Redis)
_search_context = {}


@router.get("/search-two-step/", response_model=dict)
async def search_two_step(
    name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Первый этап поиска - только по названию и городу
    Возвращает доступные формы для уточнения и создает контекст поиска
    """
    if not name:
        raise HTTPException(
            status_code=400, detail="Параметр 'name' обязателен для поиска"
        )

    query = select(Product).options(joinedload(Product.pharmacy)).join(Pharmacy)

    filters = []
    if name:
        filters.append(Product.name.ilike(f"%{name}%"))
    if city and city != "Все города":
        filters.append(Pharmacy.city.ilike(f"%{city}%"))

    if filters:
        query = query.where(or_(*filters))

    result = await db.execute(query)
    products = result.unique().scalars().all()

    if not products:
        return {
            "available_forms": [],
            "preview_products": [],
            "total_found": 0,
            "filters": {"name": name, "city": city},
            "search_id": None,
            "message": "Товары не найдены",
        }

    # Собираем уникальные формы из найденных продуктов
    available_forms = set()
    preview_products = []

    product_ids = []  # Сохраняем ID продуктов для второго этапа

    for product in products[:10]:  # Первые 10 для превью
        available_forms.add(product.form)
        product_ids.append(str(product.uuid))
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

    # Создаем контекст поиска с ID найденных продуктов
    search_id = str(uuid.uuid4())
    _search_context[search_id] = {
        "product_ids": product_ids,
        "name": name,
        "city": city,
        "available_forms": list(available_forms),
        "created_at": func.now(),
    }

    return {
        "available_forms": sorted(list(available_forms)),
        "preview_products": preview_products,
        "total_found": len(products),
        "filters": {"name": name, "city": city},
        "search_id": search_id,  # Возвращаем ID для второго этапа
    }


@router.get("/search/", response_model=dict)
async def search_products(
    search_id: Optional[str] = Query(None),  # ID из первого этапа
    form: Optional[str] = Query(None),  # Выбранная форма
    name: Optional[str] = Query(
        None
    ),  # Можно передать напрямую (для обратной совместимости)
    city: Optional[str] = Query(None),  # Можно передать напрямую
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Второй этап поиска - с выбранной формой препарата
    Может использовать контекст поиска из первого этапа
    """
    # Определяем контекст поиска
    if search_id and search_id in _search_context:
        # Используем сохраненный контекст
        context = _search_context[search_id]
        search_name = context["name"]
        search_city = context["city"]
        product_ids = context["product_ids"]

        # Удаляем использованный контекст (очистка памяти)
        del _search_context[search_id]

        # Базовый запрос с фильтрацией по ID из первого этапа
        query = (
            select(Product)
            .options(joinedload(Product.pharmacy))
            .join(Pharmacy)
            .where(Product.uuid.in_([uuid.UUID(pid) for pid in product_ids]))
        )

    else:
        # Прямой поиск (для обратной совместимости)
        search_name = name
        search_city = city

        query = select(Product).options(joinedload(Product.pharmacy)).join(Pharmacy)
        filters = []
        if search_name:
            filters.append(Product.name.ilike(f"%{search_name}%"))
        if search_city and search_city != "Все города":
            filters.append(Pharmacy.city.ilike(f"%{search_city}%"))

        if filters:
            query = query.where(or_(*filters))

    # Добавляем фильтр по форме, если указана
    if form:
        query = query.where(Product.form == form)

    # Выполняем запрос
    result = await db.execute(query)
    products = result.unique().scalars().all()

    # Группируем продукты
    grouped_products = {}
    for product in products:
        pharmacy = product.pharmacy

        key = (
            product.name,
            product.form,
            pharmacy.name if pharmacy else "Unknown",
            pharmacy.city if pharmacy else "Unknown",
            pharmacy.pharmacy_number if pharmacy else "N/A",
        )

        if key not in grouped_products:
            grouped_products[key] = {
                "name": product.name,
                "form": product.form,
                "pharmacy_name": pharmacy.name if pharmacy else "Unknown",
                "pharmacy_city": pharmacy.city if pharmacy else "Unknown",
                "pharmacy_address": pharmacy.address if pharmacy else "Unknown",
                "pharmacy_phone": pharmacy.phone if pharmacy else "Unknown",
                "pharmacy_number": pharmacy.pharmacy_number if pharmacy else "N/A",
                "price": float(product.price) if product.price else 0.0,
                "quantity": float(product.quantity) if product.quantity else 0.0,
                "manufacturer": product.manufacturer,
                "country": product.country,
                "pharmacies": [],
                "updated_at": product.updated_at,
            }
        else:
            if product.updated_at > grouped_products[key]["updated_at"]:
                grouped_products[key]["updated_at"] = product.updated_at

            grouped_products[key]["quantity"] += (
                float(product.quantity) if product.quantity else 0.0
            )

        if pharmacy:
            grouped_products[key]["pharmacies"].append(
                {
                    "pharmacy_name": pharmacy.name,
                    "pharmacy_number": pharmacy.pharmacy_number,
                    "pharmacy_city": pharmacy.city,
                    "pharmacy_address": pharmacy.address,
                    "pharmacy_phone": pharmacy.phone,
                }
            )

    # Преобразуем в список для пагинации
    grouped_products_list = list(grouped_products.values())

    # Пагинация
    total = len(grouped_products_list)
    total_pages = ceil(total / size) if total > 0 else 1
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_items = grouped_products_list[start_idx:end_idx]

    # Получаем уникальные города и формы для фильтров
    cities_query = select(Pharmacy.city).distinct().order_by(Pharmacy.city)
    cities_result = await db.execute(cities_query)
    unique_cities = [row[0] for row in cities_result.all() if row[0]]

    forms_query = select(Product.form).distinct().order_by(Product.form)
    forms_result = await db.execute(forms_query)
    unique_forms = [row[0] for row in forms_result.all() if row[0]]

    return {
        "items": paginated_items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "unique_cities": unique_cities,
        "unique_forms": unique_forms,
        "filters": {"name": search_name, "city": search_city, "form": form},
        "search_used_context": bool(search_id and search_id in _search_context),
    }


@router.get("/forms-by-name/")
async def get_forms_by_name(
    name: str = Query(..., description="Название препарата"),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить доступные формы для конкретного названия препарата
    (Альтернативный подход без сохранения контекста)
    """
    query = (
        select(Product.form)
        .distinct()
        .join(Pharmacy)
        .where(Product.name.ilike(f"%{name}%"))
    )

    if city and city != "Все города":
        query = query.where(Pharmacy.city.ilike(f"%{city}%"))

    query = query.order_by(Product.form)

    result = await db.execute(query)
    forms = [row[0] for row in result.all() if row[0]]

    return {"name": name, "city": city, "available_forms": forms}


# Остальные эндпоинты остаются без изменений
@router.get("/cities/")
async def get_cities(db: AsyncSession = Depends(get_db)):
    """Получить список уникальных городов"""
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
    """Получить список уникальных форм препаратов"""
    result = await db.execute(
        select(Product.form)
        .distinct()
        .order_by(Product.form)
        .where(Product.form.isnot(None))
    )
    forms = [row[0] for row in result.all() if row[0]]
    return forms


@router.get("/products/{product_id}")
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Получить детальную информацию о продукте"""
    result = await db.execute(
        select(Product)
        .options(joinedload(Product.pharmacy))
        .where(Product.uuid == product_id)
    )
    product = result.unique().scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "uuid": product.uuid,
        "name": product.name,
        "form": product.form,
        "manufacturer": product.manufacturer,
        "country": product.country,
        "price": float(product.price) if product.price else 0.0,
        "quantity": float(product.quantity) if product.quantity else 0.0,
        "pharmacy": (
            {
                "name": product.pharmacy.name if product.pharmacy else None,
                "city": product.pharmacy.city if product.pharmacy else None,
                "address": product.pharmacy.address if product.pharmacy else None,
                "phone": product.pharmacy.phone if product.pharmacy else None,
            }
            if product.pharmacy
            else None
        ),
    }


@router.get("/pharmacies/{pharmacy_id}")
async def get_pharmacy(pharmacy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Получить информацию об аптеке"""
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()

    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    return pharmacy
