"""CRUD заказов бронирования и pharmacy API."""

import uuid
import logging
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import get_db
from db.models import Pharmacy, Product
from db.booking_models import BookingOrder, PharmacyAPIConfig
from db.booking_schemas import (
    BookingOrderCreate,
    BookingOrderResponse,
    OrderCancelRequest,
    OrderStatusUpdate,
    PharmacyAPIConfigCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orders", response_model=BookingOrderResponse)
async def create_booking_order(
    order_data: BookingOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Создание заказа бронирования"""
    try:
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

        order = BookingOrder(
            uuid=uuid.uuid4(),
            pharmacy_id=order_data.pharmacy_id,
            product_id=order_data.product_id,
            product_name=product.name,
            product_form=product.form,
            product_manufacturer=product.manufacturer,
            product_country=product.country,
            product_price=product.price,
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


@router.get("/orders", response_model=List[BookingOrderResponse])
async def get_orders(
    pharmacy_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение списка заказов с фильтрацией"""
    try:
        query = select(BookingOrder).options(selectinload(BookingOrder.pharmacy))
        if pharmacy_id:
            query = query.where(BookingOrder.pharmacy_id == pharmacy_id)
        if status:
            query = query.where(BookingOrder.status == status)
        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().unique().all()

        response_orders = []
        for order in orders:
            pharmacy = order.pharmacy

            order_dict = {
                "uuid": str(order.uuid),
                "status": order.status,
                "created_at": (
                    order.created_at.isoformat() if order.created_at else None
                ),
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
                "pharmacy_opening_hours": pharmacy.opening_hours if pharmacy else None,
                "pharmacy_address": pharmacy.address if pharmacy else None,
                "pharmacy_phone": pharmacy.phone if pharmacy else None,
            }
            response_orders.append(order_dict)

        return response_orders

    except Exception as e:
        logger.exception("Error fetching orders")
        raise HTTPException(status_code=500, detail="Error fetching orders")


@router.get("/orders/{order_id}", response_model=BookingOrderResponse)
async def get_order_by_id(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Получение заказа по ID"""
    try:
        result = await db.execute(
            select(BookingOrder).where(BookingOrder.uuid == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching order {order_id}")
        raise HTTPException(status_code=500, detail="Error fetching order")


@router.patch("/orders/{order_id}")
async def update_order_status(
    order_id: uuid.UUID,
    update_data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновление статуса заказа с комментарием"""
    from routers.orders_helpers import send_order_status_notification

    try:
        status = update_data.status
        comment = update_data.comment or ""

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

        if status == "cancelled" and comment:
            order.cancellation_reason = comment
            order.cancelled_at = datetime.utcnow()
        elif status == "failed" and comment:
            order.cancellation_reason = comment

        order.updated_at = datetime.utcnow()
        await db.commit()

        if old_status != status:
            await send_order_status_notification(order, old_status, status, db, comment)

        logger.info(
            f"Order {order_id} status manually updated from {old_status} to {status}. Comment: {comment}"
        )

        return {
            "status": "updated",
            "order_id": str(order_id),
            "previous_status": old_status,
            "new_status": status,
            "comment": comment,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error updating order {order_id} status")
        raise HTTPException(status_code=500, detail="Error updating order status")


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: uuid.UUID,
    cancel_request: OrderCancelRequest,
    db: AsyncSession = Depends(get_db),
):
    """Отмена заказа с причиной"""
    from routers.orders_helpers import send_order_status_notification

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

        old_status = order.status
        order.status = "cancelled"
        order.cancelled_at = datetime.utcnow()
        order.cancellation_reason = (
            cancel_request.reason if cancel_request.reason else "Отменено пользователем"
        )
        order.updated_at = datetime.utcnow()
        await db.commit()

        await send_order_status_notification(
            order, old_status, "cancelled", db, cancel_request.reason or ""
        )

        return {
            "status": "cancelled",
            "order_id": str(order_id),
            "message": "Order successfully cancelled",
            "reason": cancel_request.reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error cancelling order {order_id}")
        raise HTTPException(status_code=500, detail="Error cancelling order")


# ============================================================
# Pharmacy API endpoints — для C++ клиента аптеки (pull-модель)
# ============================================================


@router.post("/api/external/orders/callback")
async def external_order_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Callback endpoint для аптек — они отправляют сюда статусы заказов.
    Header: Authorization: Bearer <token> OR X-API-KEY: <token>
    Body JSON:
      - external_order_id (optional)
      - local_order_id (optional)
      - status: pending|confirmed|cancelled|failed
      - comment (optional)
    """
    from routers.orders_helpers import send_order_status_notification

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
    reason = payload.get("comment", "")

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

        # Сохраняем причину отмены, если статус cancelled и есть комментарий
        if new_status == "cancelled" and reason:
            order.cancellation_reason = reason
            order.cancelled_at = datetime.utcnow()
        elif new_status == "failed" and reason:
            order.cancellation_reason = reason

        # Сохраняем external_order_id если его ранее не было
        if external_order_id and not order.external_order_id:
            order.external_order_id = external_order_id

        order.updated_at = datetime.utcnow()

        await db.commit()

        # Отправляем уведомление в Telegram с комментарием от аптеки
        if old_status != new_status:
            await send_order_status_notification(
                order, old_status, new_status, db, reason
            )

        logger.info(
            f"Order {order.uuid} status updated from {old_status} to {new_status} via pharmacy callback. Comment: {reason}"
        )

        return {
            "status": "success",
            "order_id": str(order.uuid),
            "previous_status": old_status,
            "new_status": new_status,
            "comment": reason,
        }

    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Failed to update order status from pharmacy callback: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to update order")


@router.get(
    "/pharmacies/{pharmacy_id}/orders", response_model=List[BookingOrderResponse]
)
async def get_pharmacy_orders(
    pharmacy_id: uuid.UUID,
    status: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение заказов конкретной аптеки с аутентификацией"""
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
        select(PharmacyAPIConfig).where(PharmacyAPIConfig.is_active == True)
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
        raise HTTPException(
            status_code=403, detail="Invalid token or pharmacy access denied"
        )

    # Проверяем существование аптеки
    pharmacy_result = await db.execute(
        select(Pharmacy).where(Pharmacy.uuid == pharmacy_id)
    )
    pharmacy = pharmacy_result.scalar_one_or_none()

    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Получаем заказы
    query = select(BookingOrder).where(BookingOrder.pharmacy_id == pharmacy_id)

    if status:
        query = query.where(BookingOrder.status == status)

    query = query.order_by(BookingOrder.created_at.desc())

    result = await db.execute(query)
    orders = result.scalars().all()

    # Формируем ответ со всеми полями
    response_orders = []
    for order in orders:
        order_dict = {
            "uuid": order.uuid,
            "external_order_id": order.external_order_id,
            "pharmacy_id": order.pharmacy_id,
            "product_id": order.product_id,
            "status": order.status,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "quantity": order.quantity,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "telegram_id": order.telegram_id,
            "product_name": order.product_name,
            "product_form": order.product_form,
            "product_manufacturer": order.product_manufacturer,
            "product_country": order.product_country,
            "product_price": (
                float(order.product_price) if order.product_price else None
            ),
            "product_serial": order.product_serial,
            "cancelled_at": order.cancelled_at,
            "cancellation_reason": order.cancellation_reason,
            "pharmacy_opening_hours": pharmacy.opening_hours if pharmacy else None,
            "pharmacy_address": pharmacy.address if pharmacy else None,
            "pharmacy_phone": pharmacy.phone if pharmacy else None,
        }
        response_orders.append(order_dict)

    return response_orders


@router.post("/pharmacies/register")
async def register_pharmacy(
    config_data: PharmacyAPIConfigCreate, db: AsyncSession = Depends(get_db)
):
    """Регистрация новой аптеки — только токен для pull-модели"""
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

    # Создаем конфигурацию
    api_config = PharmacyAPIConfig(
        uuid=uuid.uuid4(),
        pharmacy_id=config_data.pharmacy_id,
        api_type="pull",
        endpoint_url=config_data.endpoint_url,
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
        "auth_token": auth_token,
        "mode": "pull",
        "endpoints": {
            "get_orders": f"/pharmacies/{config_data.pharmacy_id}/orders?status=pending",
            "update_status": "/api/external/orders/callback",
        },
        "message": "Use this token to authenticate pharmacy requests",
    }


@router.post("/pharmacies/login")
async def pharmacy_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Вход для аптеки — получение информации по токену"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )

    token = auth_header[7:]

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
            "pharmacy_number": pharmacy.pharmacy_number,
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
        except Exception:
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

    if "auth_token" in data and data["auth_token"]:
        api_config.set_auth_token(data["auth_token"])

    api_config.last_sync_at = datetime.utcnow()
    await db.commit()

    return {"status": "updated"}
