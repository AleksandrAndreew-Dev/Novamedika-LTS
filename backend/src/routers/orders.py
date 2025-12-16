# orders.py - исправленная версия импортов

import uuid
import logging

import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.database import get_db, async_session_maker
from db.models import Pharmacy, Product
from db.booking_models import BookingOrder, PharmacyAPIConfig, SyncLog
from db.booking_schemas import (
    BookingOrderCreate,
    BookingOrderResponse,
    PharmacyAPIConfigCreate,
)

from db.qa_models import User
from sqlalchemy import func


logger = logging.getLogger(__name__)
router = APIRouter()


# orders.py (функция create_booking_order)

@router.post("/orders", response_model=BookingOrderResponse)
async def create_booking_order(
    order_data: BookingOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Создание заказа бронирования - только локальное сохранение"""
    try:
        # Проверяем существование аптеки и продукта
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == order_data.pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        product_result = await db.execute(
            select(Product).where(Product.uuid == order_data.product_id)
        )
        product = product_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Создаем заказ в нашей системе с КЭШИРОВАННЫМИ ДАННЫМИ ПРОДУКТА
        order = BookingOrder(
            uuid=uuid.uuid4(),
            pharmacy_id=order_data.pharmacy_id,
            product_id=order_data.product_id,

            # КЭШИРОВАННЫЕ ДАННЫЕ ПРОДУКТА (ЗАПОЛНЯЕМ ВСЕ ПОЛЯ!)
            product_name=product.name,
            product_form=product.form,  # ВАЖНО: форма продукта
            product_manufacturer=product.manufacturer,
            product_country=product.country,
            product_price=product.price,  # ВАЖНО: цена продукта
            product_serial=product.serial,

            quantity=order_data.quantity,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            scheduled_pickup=order_data.scheduled_pickup,
            status="pending",
            telegram_id=order_data.telegram_id,
        )

        db.add(order)
        await db.commit()
        await db.refresh(order)

        logger.info(f"Created booking order {order.uuid} for pharmacy {pharmacy.name}")
        return order

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error creating booking order")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/external/orders/callback")
async def external_order_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Callback endpoint для аптек - они отправляют сюда статусы заказов
    Header: Authorization: Bearer <token> OR X-API-KEY: <token>
    Body JSON:
      - external_order_id (optional)
      - local_order_id (optional)
      - status: pending|confirmed|cancelled|failed
      - reason (optional)
    """
    # Аутентификация по токену
    auth = request.headers.get("Authorization")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.headers.get("X-API-KEY")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    # Находим конфигурацию аптеки по токену
    config_result = await db.execute(
        select(PharmacyAPIConfig).where(PharmacyAPIConfig.is_active == True)
    )
    configs = config_result.scalars().all()

    api_config = None
    for config in configs:
        try:
            if config.get_auth_token() == token:
                api_config = config
                break
        except Exception as e:
            logger.warning(f"Error decrypting token for config {config.uuid}: {e}")
            continue

    if not api_config:
        raise HTTPException(status_code=403, detail="Invalid or inactive token")

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    external_order_id = payload.get("external_order_id")
    local_order_id = payload.get("local_order_id")
    new_status = payload.get("status")
    reason = payload.get("reason", "")

    if not new_status:
        raise HTTPException(status_code=400, detail="status field is required")

    if not external_order_id and not local_order_id:
        raise HTTPException(
            status_code=400,
            detail="Either external_order_id or local_order_id is required",
        )

    # Валидация статуса
    valid_statuses = ["pending", "confirmed", "cancelled", "failed"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    # Поиск заказа
    order = None
    if external_order_id:
        order_result = await db.execute(
            select(BookingOrder).where(
                BookingOrder.external_order_id == external_order_id,
                BookingOrder.pharmacy_id == api_config.pharmacy_id,
            )
        )
        order = order_result.scalar_one_or_none()

    if not order and local_order_id:
        try:
            order_uuid = uuid.UUID(local_order_id)
            order_result = await db.execute(
                select(BookingOrder).where(
                    BookingOrder.uuid == order_uuid,
                    BookingOrder.pharmacy_id == api_config.pharmacy_id,
                )
            )
            order = order_result.scalar_one_or_none()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid local_order_id format")

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Обновляем статус
    try:
        old_status = order.status
        order.status = new_status

        # Сохраняем external_order_id если его ранее не было
        if external_order_id and not order.external_order_id:
            order.external_order_id = external_order_id

        order.updated_at = datetime.utcnow()

        await db.commit()

        # Отправляем уведомление в Telegram с комментарием от аптеки
        if old_status != new_status:
            await send_order_status_notification(order, old_status, new_status, db, reason)

        logger.info(
            f"Order {order.uuid} status updated from {old_status} to {new_status} via pharmacy callback. Comment: {reason}"
        )

        return {
            "status": "success",
            "order_id": str(order.uuid),
            "previous_status": old_status,
            "new_status": new_status,
        }

    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Failed to update order status from pharmacy callback: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to update order")


@router.get("/orders", response_model=List[BookingOrderResponse])
async def get_orders(
    pharmacy_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение списка заказов с фильтрацией и информацией о продукте"""
    try:
        query = select(BookingOrder)

        if pharmacy_id:
            query = query.where(BookingOrder.pharmacy_id == pharmacy_id)
        if status:
            query = query.where(BookingOrder.status == status)

        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        # Получаем информацию об аптеках
        response_orders = []
        for order in orders:
            # Получаем информацию об аптеке
            pharmacy_result = await db.execute(
                select(Pharmacy).where(Pharmacy.uuid == order.pharmacy_id)
            )
            pharmacy = pharmacy_result.scalar_one_or_none()

            order_dict = {
                "uuid": str(order.uuid),
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "telegram_id": order.telegram_id,
                "product_name": order.product_name,
                "product_form": order.product_form,
                "product_manufacturer": order.product_manufacturer,
                "product_country": order.product_country,
                "product_price": order.product_price,
                "product_serial": order.product_serial,
                "quantity": order.quantity,
                # Добавляем информацию об аптеке
                "pharmacy_opening_hours": pharmacy.opening_hours if pharmacy else None,
                "pharmacy_address": pharmacy.address if pharmacy else None,
                "pharmacy_phone": pharmacy.phone if pharmacy else None,
            }
            response_orders.append(order_dict)

        return response_orders

    except Exception as e:
        logger.exception("Error fetching orders")
        raise HTTPException(status_code=500, detail="Error fetching orders")


# orders.py (функция get_order_by_id)

@router.get("/orders/{order_id}", response_model=BookingOrderResponse)
async def get_order_by_id(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Получение заказа по ID с информацией о продукте"""
    try:
        result = await db.execute(
            select(BookingOrder).where(BookingOrder.uuid == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return order  # Все данные уже в order

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching order {order_id}")
        raise HTTPException(status_code=500, detail="Error fetching order")


@router.patch("/orders/{order_id}")
async def update_order_status(
    order_id: uuid.UUID, status: str, db: AsyncSession = Depends(get_db)
):
    """Обновление статуса заказа"""
    try:
        # Валидация статуса
        valid_statuses = ["pending", "submitted", "confirmed", "cancelled", "failed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )

        result = await db.execute(
            select(BookingOrder).where(BookingOrder.uuid == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        old_status = order.status
        order.status = status
        order.updated_at = datetime.utcnow()

        await db.commit()

        # Отправляем уведомление без комментария (пустая строка)
        if old_status != status and status in ["confirmed", "cancelled", "failed"]:
            await send_order_status_notification(order, old_status, status, db, "")

        logger.info(
            f"Order {order_id} status manually updated from {old_status} to {status}"
        )

        return {
            "status": "updated",
            "order_id": str(order_id),
            "previous_status": old_status,
            "new_status": status,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error updating order {order_id} status")
        raise HTTPException(status_code=500, detail="Error updating order status")


@router.post("/pharmacies/register")
async def register_pharmacy(
    config_data: PharmacyAPIConfigCreate, db: AsyncSession = Depends(get_db)
):
    """Регистрация новой аптеки - только токен для pull-модели"""
    try:
        # Проверяем существование аптеки
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == config_data.pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")

        # Проверяем, нет ли уже конфигурации
        existing_result = await db.execute(
            select(PharmacyAPIConfig).where(
                PharmacyAPIConfig.pharmacy_id == config_data.pharmacy_id
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="API configuration already exists for this pharmacy",
            )

        # Генерируем безопасный токен
        auth_token = secrets.token_urlsafe(32)

        # Создаем конфигурацию - endpoint_url не обязателен в pull-модели
        api_config = PharmacyAPIConfig(
            uuid=uuid.uuid4(),
            pharmacy_id=config_data.pharmacy_id,
            api_type="pull",  # Указываем что аптека сама опрашивает
            endpoint_url=config_data.endpoint_url,  # Может быть null
            auth_type="bearer",
            sync_from_date=config_data.sync_from_date,
            is_active=config_data.is_active,
        )
        api_config.set_auth_token(auth_token)

        db.add(api_config)
        await db.commit()

        return {
            "status": "success",
            "pharmacy_id": str(config_data.pharmacy_id),
            "auth_token": auth_token,  # Токен для аутентификации аптеки
            "mode": "pull",  # Режим работы - аптека опрашивает сервер
            "endpoints": {
                "get_orders": f"/pharmacies/{config_data.pharmacy_id}/orders?status=pending",
                "update_status": "/api/external/orders/callback",
            },
            "message": "Use this token to authenticate pharmacy requests",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Pharmacy registration failed")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/pharmacies/login")
async def pharmacy_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Вход для аптеки - получение информации по токену"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )

    token = auth_header[7:]  # Remove "Bearer "

    # Ищем конфиг по токену
    config_result = await db.execute(
        select(PharmacyAPIConfig, Pharmacy)
        .join(Pharmacy, PharmacyAPIConfig.pharmacy_id == Pharmacy.uuid)
        .where(PharmacyAPIConfig.is_active == True)
    )
    results = config_result.all()

    api_config = None
    pharmacy = None

    for config, pharm in results:
        try:
            if config.get_auth_token() == token:
                api_config = config
                pharmacy = pharm
                break
        except Exception as e:
            logger.warning(f"Error decrypting token for pharmacy {pharm.uuid}: {e}")
            continue

    if not api_config:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "pharmacy": {
            "uuid": str(pharmacy.uuid),
            "name": pharmacy.name,
            "number": pharmacy.pharmacy_number,
            "city": pharmacy.city,
            "address": pharmacy.address,
            "phone": pharmacy.phone,
            "opening_hours": pharmacy.opening_hours,
        },
        "api_config": {
            "api_type": api_config.api_type,
            "endpoint_url": api_config.endpoint_url,
            "auth_type": api_config.auth_type,
            "last_sync": api_config.last_sync_at,
            "is_active": api_config.is_active,
        },
    }


@router.put("/pharmacies/config")
async def update_pharmacy_config(request: Request, db: AsyncSession = Depends(get_db)):
    """Обновление конфигурации API аптеки"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")

    token = auth_header[7:]

    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Находим конфиг
    config_result = await db.execute(
        select(PharmacyAPIConfig)
        .join(Pharmacy, PharmacyAPIConfig.pharmacy_id == Pharmacy.uuid)
        .where(PharmacyAPIConfig.is_active == True)
    )
    results = config_result.scalars().all()

    api_config = None
    for config in results:
        try:
            if config.get_auth_token() == token:
                api_config = config
                break
        except Exception as e:
            continue

    if not api_config:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Обновляем поля
    if "endpoint_url" in data:
        api_config.endpoint_url = data["endpoint_url"]
    if "api_type" in data:
        api_config.api_type = data["api_type"]
    if "auth_type" in data:
        api_config.auth_type = data["auth_type"]
    if "is_active" in data:
        api_config.is_active = data["is_active"]

    # Если предоставлен новый токен
    if "auth_token" in data and data["auth_token"]:
        api_config.set_auth_token(data["auth_token"])

    api_config.last_sync_at = datetime.utcnow()
    await db.commit()

    return {"status": "updated"}


# orders.py - исправленный код функции get_pharmacy_orders

@router.get("/pharmacies/{pharmacy_id}/orders", response_model=List[BookingOrderResponse])
async def get_pharmacy_orders(
    pharmacy_id: uuid.UUID,
    status: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение заказов конкретной аптеки с аутентификацией"""
    try:
        # Аутентификация по токену
        auth_header = request.headers.get("Authorization") if request else None
        token = None
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            token = request.headers.get("X-API-KEY") if request else None

        if not token:
            raise HTTPException(status_code=401, detail="Missing auth token")

        # Проверяем токен и принадлежность к аптеке
        config_result = await db.execute(
            select(PharmacyAPIConfig).where(
                PharmacyAPIConfig.is_active == True
            )
        )
        configs = config_result.scalars().all()

        api_config = None
        for config in configs:
            try:
                if config.get_auth_token() == token and config.pharmacy_id == pharmacy_id:
                    api_config = config
                    break
            except Exception as e:
                logger.warning(f"Error decrypting token for config {config.uuid}: {e}")
                continue

        if not api_config:
            raise HTTPException(status_code=403, detail="Invalid token or pharmacy access denied")

        # Проверяем существование аптеки
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")

        # Получаем заказы с загрузкой отношений
        from sqlalchemy.orm import selectinload

        query = select(BookingOrder).where(BookingOrder.pharmacy_id == pharmacy_id)

        if status:
            query = query.where(BookingOrder.status == status)

        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        # Создаем правильный ответ с ВСЕМИ полями, которые ожидает схема
        response_orders = []
        for order in orders:
            # Используем стандартную сериализацию через Pydantic
            # Преобразуем order в словарь с ВСЕМИ полями
            order_dict = {
                # Обязательные поля из схемы
                "uuid": order.uuid,
                "external_order_id": order.external_order_id,  # Может быть None
                "pharmacy_id": order.pharmacy_id,
                "product_id": order.product_id,  # Может быть None
                "status": order.status,
                "created_at": order.created_at,
                "updated_at": order.updated_at,

                # Поля из BookingOrderBase
                "quantity": order.quantity,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "telegram_id": order.telegram_id,

                # Кэшированные данные продукта
                "product_name": order.product_name,
                "product_form": order.product_form,
                "product_manufacturer": order.product_manufacturer,
                "product_country": order.product_country,
                "product_price": float(order.product_price) if order.product_price else None,
                "product_serial": order.product_serial,

                # Поля для отмены
                "cancelled_at": order.cancelled_at,
                "cancellation_reason": order.cancellation_reason,

                # Дополнительные поля для аптеки (для C++ клиента)
                "pharmacy_opening_hours": pharmacy.opening_hours if pharmacy else None,
                "pharmacy_address": pharmacy.address if pharmacy else None,
                "pharmacy_phone": pharmacy.phone if pharmacy else None,
            }
            response_orders.append(order_dict)

        return response_orders

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching orders for pharmacy {pharmacy_id}")
        raise HTTPException(status_code=500, detail="Error fetching orders")


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Отмена заказа"""
    try:
        result = await db.execute(
            select(BookingOrder).where(BookingOrder.uuid == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status in ["cancelled", "failed"]:
            raise HTTPException(
                status_code=400, detail=f"Order is already {order.status}"
            )

        # Если заказ уже подтвержден, может потребоваться дополнительная логика
        if order.status == "confirmed":
            # TODO: Уведомить внешнюю систему об отмене
            pass

        order.status = "cancelled"
        order.updated_at = datetime.utcnow()

        await db.commit()

        return {
            "status": "cancelled",
            "order_id": str(order_id),
            "message": "Order successfully cancelled",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error cancelling order {order_id}")
        raise HTTPException(status_code=500, detail="Error cancelling order")


async def get_user_telegram_id_by_order(
    order: BookingOrder, db: AsyncSession
) -> Optional[int]:
    """Получить telegram_id пользователя по заказу - УЛУЧШЕННАЯ ВЕРСИЯ"""
    try:
        # 1. Пробуем получить telegram_id напрямую из заказа
        if order.telegram_id:
            return order.telegram_id

        # 2. Если в заказе нет, ищем по телефону в таблице пользователей
        if order.customer_phone:
            result = await db.execute(
                select(User).where(User.phone == order.customer_phone)
            )
            user = result.scalar_one_or_none()
            if user and user.telegram_id:
                return user.telegram_id

        logger.warning(
            f"No telegram_id found for order {order.uuid}, phone: {order.customer_phone}"
        )
        return None

    except Exception as e:
        logger.error(f"Error getting telegram_id for order {order.uuid}: {e}")
        return None


async def get_pharmacy_name(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить название аптеки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        result = await db.execute(select(Pharmacy.name).where(Pharmacy.uuid == pharmacy_id))
        pharmacy_name = result.scalar_one_or_none()
        return pharmacy_name if pharmacy_name else "Неизвестная аптека"
    except Exception as e:
        logger.error(f"Error getting pharmacy name for {pharmacy_id}: {e}")
        return "Неизвестная аптека"

async def get_pharmacy_phone(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить телефон аптеки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        result = await db.execute(select(Pharmacy.phone).where(Pharmacy.uuid == pharmacy_id))
        phone = result.scalar_one_or_none()
        return phone if phone else "Не указан"
    except Exception as e:
        logger.error(f"Error getting pharmacy phone for {pharmacy_id}: {e}")
        return "Не указан"

async def get_pharmacy_address(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить адрес аптеки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        result = await db.execute(select(Pharmacy.address).where(Pharmacy.uuid == pharmacy_id))
        address = result.scalar_one_or_none()
        return address if address else "Адрес не указан"
    except Exception as e:
        logger.error(f"Error getting pharmacy address for {pharmacy_id}: {e}")
        return "Адрес не указан"

async def get_product_name(product_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить название товара"""
    try:
        result = await db.execute(select(Product.name).where(Product.uuid == product_id))
        product_name = result.scalar_one_or_none()
        return product_name if product_name else "Неизвестный товар"
    except Exception as e:
        logger.error(f"Error getting product name for {product_id}: {e}")
        return "Неизвестный товар"

async def get_pharmacy_number(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить номер аптеки"""
    try:
        result = await db.execute(select(Pharmacy.pharmacy_number).where(Pharmacy.uuid == pharmacy_id))
        pharmacy_number = result.scalar_one_or_none()
        return pharmacy_number if pharmacy_number else ""
    except Exception as e:
        logger.error(f"Error getting pharmacy number for {pharmacy_id}: {e}")
        return ""

async def get_pharmacy_opening_hours(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить время работы аптеки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        result = await db.execute(select(Pharmacy.opening_hours).where(Pharmacy.uuid == pharmacy_id))
        opening_hours = result.scalar_one_or_none()
        return opening_hours if opening_hours else "Не указано"
    except Exception as e:
        logger.error(f"Error getting pharmacy opening hours for {pharmacy_id}: {e}")
        return "Не указано"

async def send_order_status_notification(
    order: BookingOrder, old_status: str, new_status: str, db: AsyncSession, comment: str = ""
):
    """Отправка уведомления о статусе заказа в Telegram с комментарием от аптеки"""
    try:
        # Получаем telegram_id пользователя
        telegram_id = await get_user_telegram_id_by_order(order, db)

        if not telegram_id:
            logger.info(f"No telegram_id for order {order.uuid}, skipping notification")
            return

        # Инициализируем бота
        from bot.core import bot_manager

        bot, _ = await bot_manager.initialize()

        if not bot:
            logger.error("Bot not initialized for sending order notification")
            return

        # Получаем информацию об аптеке и товаре
        pharmacy_name = await get_pharmacy_name(order.pharmacy_id, db)
        pharmacy_number = await get_pharmacy_number(order.pharmacy_id, db)
        pharmacy_phone = await get_pharmacy_phone(order.pharmacy_id, db)
        pharmacy_address = await get_pharmacy_address(order.pharmacy_id, db)
        pharmacy_opening_hours = await get_pharmacy_opening_hours(order.pharmacy_id, db)  # НОВАЯ СТРОКА
        product_name = await get_product_name(order.product_id, db)

        # Получаем форму и цену товара из заказа
        product_form = order.product_form or "Не указана"
        product_price = order.product_price or 0.0

        # Форматируем цену
        price_formatted = f"{product_price:.2f}" if product_price else "0.00"

        # Рассчитываем общую стоимость
        total_price = product_price * order.quantity if product_price else 0.0
        total_formatted = f"{total_price:.2f}" if total_price else "0.00"

        # Формируем полное название аптеки с номером
        pharmacy_full_name = pharmacy_name
        if pharmacy_number:
            pharmacy_full_name += f" №{pharmacy_number}"

        # Форматируем сообщение в зависимости от статуса
        if new_status == "confirmed":
            message_text = (
                "✅ **Ваш заказ подтвержден!**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🛍️ Товар: {product_name}\n"
                f"💊 Форма: {product_form}\n"
                f"💰 Цена за единицу: {price_formatted} руб.\n"
                f"📊 Количество: {order.quantity}\n"
                f"💵 Общая стоимость: {total_formatted} руб.\n"
                f"🏪 Аптека: {pharmacy_full_name}\n"
                f"📍 Адрес: {pharmacy_address}\n"
                f"📞 Телефон: {pharmacy_phone}\n"
                f"🕐 Время работы: {pharmacy_opening_hours}\n"  # НОВАЯ СТРОКА
            )

            # Добавляем комментарий от аптеки, если есть
            if comment:
                message_text += f"📝 **Комментарий от аптеки:** {comment}\n\n"
            else:
                message_text += "\n"

            message_text += "Можете забирать ваш заказ! 🎉"

        elif new_status == "cancelled":
            message_text = (
                "❌ **Ваш заказ отменен**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🛍️ Товар: {product_name}\n"
                f"💊 Форма: {product_form}\n"
                f"💰 Цена за единицу: {price_formatted} руб.\n"
                f"📊 Количество: {order.quantity}\n"
                f"💵 Общая стоимость: {total_formatted} руб.\n"
                f"🏪 Аптека: {pharmacy_full_name}\n"
                f"📞 Телефон: {pharmacy_phone}\n"
            )

            # Добавляем комментарий от аптеки, если есть
            if comment:
                message_text += f"📝 **Причина отмены:** {comment}\n\n"
            else:
                message_text += "\n"

            message_text += "Если это ошибка, свяжитесь с аптекой по телефону выше."

        elif new_status == "failed":
            message_text = (
                "⚠️ **Проблема с вашим заказом**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🛍️ Товар: {product_name}\n"
                f"💊 Форма: {product_form}\n"
                f"💰 Цена за единицу: {price_formatted} руб.\n"
                f"📊 Количество: {order.quantity}\n"
                f"💵 Общая стоимость: {total_formatted} руб.\n"
                f"🏪 Аптека: {pharmacy_full_name}\n"
                f"📞 Телефон: {pharmacy_phone}\n"
            )

            # Добавляем комментарий от аптеки, если есть
            if comment:
                message_text += f"📝 **Причина проблемы:** {comment}\n\n"
            else:
                message_text += "\n"

            message_text += "Техническая ошибка при обработке заказа. Мы уже работаем над решением."
        else:
            return  # Не отправляем уведомление для других статусов

        # Отправляем сообщение
        await bot.send_message(
            chat_id=telegram_id,
            text=message_text,
            parse_mode="Markdown"
        )
        logger.info(
            f"Order status notification sent to user {telegram_id} for order {order.uuid} with comment: {comment}"
        )

    except Exception as e:
        logger.error(
            f"Failed to send order status notification for order {order.uuid}: {e}"
        )
