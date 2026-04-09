"""CRUD заказов бронирования."""

import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import Pharmacy, Product
from db.booking_models import BookingOrder
from db.booking_schemas import (
    BookingOrderCreate,
    BookingOrderResponse,
    OrderCancelRequest,
    OrderStatusUpdate,
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
        query = select(BookingOrder)
        if pharmacy_id:
            query = query.where(BookingOrder.pharmacy_id == pharmacy_id)
        if status:
            query = query.where(BookingOrder.status == status)
        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        response_orders = []
        for order in orders:
            pharmacy_result = await db.execute(
                select(Pharmacy).where(Pharmacy.uuid == order.pharmacy_id)
            )
            pharmacy = pharmacy_result.scalar_one_or_none()

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
            await send_order_status_notification(
                order, old_status, status, db, comment
            )

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
