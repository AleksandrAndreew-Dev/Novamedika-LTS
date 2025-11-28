# orders.py - исправленная версия импортов

import uuid
import logging
import asyncio
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
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
from order_manager.manager import ExternalAPIManager
from db.qa_models import User
from sqlalchemy import func


logger = logging.getLogger(__name__)
router = APIRouter()
api_manager = ExternalAPIManager()


@router.post("/orders", response_model=BookingOrderResponse)
async def create_booking_order(
    order_data: BookingOrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Создание заказа бронирования"""
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

        # Создаем заказ в нашей системе с Telegram ID
        order = BookingOrder(
            uuid=uuid.uuid4(),
            pharmacy_id=order_data.pharmacy_id,
            product_id=order_data.product_id,
            quantity=order_data.quantity,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            scheduled_pickup=order_data.scheduled_pickup,
            status="pending",
            telegram_id=order_data.telegram_id,  # Используем переданный Telegram ID
        )

        db.add(order)
        await db.commit()
        await db.refresh(order)

        # Запускаем фоновую задачу для отправки во внешнюю систему
        background_tasks.add_task(
            submit_order_to_external_api_with_retry,
            str(order.uuid),
            str(order_data.pharmacy_id)
        )

        return order

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error creating booking order")
        raise HTTPException(status_code=500, detail="Internal server error")


async def submit_order_to_external_api_with_retry(
    order_id: str, pharmacy_id: str, max_retries: int = 3
):
    """Фоновая задача для отправки заказа во внешнюю API с повторными попытками"""
    for attempt in range(max_retries):
        try:
            success = await submit_order_to_external_api(order_id, pharmacy_id)
            if success:
                logger.info(
                    f"Successfully submitted order {order_id} to external API (attempt {attempt + 1})"
                )
                return
            else:
                logger.warning(
                    f"Failed to submit order {order_id} (attempt {attempt + 1})"
                )
        except Exception as e:
            logger.error(
                f"Error submitting order {order_id} (attempt {attempt + 1}): {str(e)}"
            )

        if attempt < max_retries - 1:
            wait_time = 2**attempt  # Exponential backoff
            logger.info(f"Retrying order {order_id} in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

    # Если все попытки неудачны, помечаем заказ как failed
    await mark_order_as_failed(order_id)


async def submit_order_to_external_api(order_id: str, pharmacy_id: str) -> bool:
    """Отправка заказа во внешнюю API"""
    async with async_session_maker() as session:
        try:
            # Получаем заказ и конфиг API аптеки
            order_result = await session.execute(
                select(BookingOrder).where(BookingOrder.uuid == uuid.UUID(order_id))
            )
            order = order_result.scalar_one_or_none()

            config_result = await session.execute(
                select(PharmacyAPIConfig).where(
                    PharmacyAPIConfig.pharmacy_id == uuid.UUID(pharmacy_id)
                )
            )
            api_config = config_result.scalar_one_or_none()

            if not order:
                logger.warning(f"Order {order_id} not found")
                return False

            if not api_config or not api_config.is_active:
                logger.warning(
                    f"API config not found or inactive for pharmacy {pharmacy_id}"
                )
                # Если API не настроен, считаем заказ успешным (локальное бронирование)
                order.status = "confirmed"
                await session.commit()
                return True

            # Получаем информацию о продукте
            product_result = await session.execute(
                select(Product).where(Product.uuid == order.product_id)
            )
            product = product_result.scalar_one_or_none()

            if not product:
                logger.warning(
                    f"Product {order.product_id} not found for order {order_id}"
                )
                return False

            # Подготавливаем данные для внешнего API
            payload = {
                "product_id": str(order.product_id),
                "product_name": product.name,
                "quantity": order.quantity,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "scheduled_pickup": (
                    order.scheduled_pickup.isoformat()
                    if order.scheduled_pickup
                    else None
                ),
                "local_order_id": str(order.uuid),
            }

            # Отправляем во внешнюю систему через менеджер
            result = await api_manager.submit_order_to_pharmacy(api_config, payload)

            # Обрабатываем результат
            if result and isinstance(result, dict):
                external_id = result.get("order_id") or result.get("external_order_id")
                if external_id:
                    order.external_order_id = str(external_id)
                    order.status = "submitted"
                else:
                    # Если внешняя система не вернула ID, но запрос успешен
                    order.status = "submitted"
            else:
                order.status = "submitted"  # Статус по умолчанию при успешной отправке

            await session.commit()
            return True

        except Exception as e:
            logger.exception(f"Failed to submit order {order_id} to external API")
            await session.rollback()
            return False


async def mark_order_as_failed(order_id: str):
    """Пометить заказ как неудачный после всех попыток"""
    async with async_session_maker() as session:
        try:
            order_result = await session.execute(
                select(BookingOrder).where(BookingOrder.uuid == uuid.UUID(order_id))
            )
            order = order_result.scalar_one_or_none()

            if order:
                order.status = "failed"
                await session.commit()
                logger.info(
                    f"Order {order_id} marked as failed after all retry attempts"
                )
        except Exception as e:
            logger.error(f"Failed to mark order {order_id} as failed: {str(e)}")


@router.post("/api/external/orders/callback")
async def external_order_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Callback endpoint для аптеки.
    Header: Authorization: Bearer <token>  OR X-API-KEY: <token>
    Body JSON:
      - external_order_id (optional если pharmacy возвращает local_order_id)
      - local_order_id (optional)
      - status: submitted|confirmed|cancelled|failed
      - reason (optional)
      - timestamp (optional)
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
    reason = payload.get("reason")
    timestamp = payload.get("timestamp")

    if not new_status:
        raise HTTPException(status_code=400, detail="status field is required")

    if not external_order_id and not local_order_id:
        raise HTTPException(
            status_code=400,
            detail="Either external_order_id or local_order_id is required",
        )

    # Валидация статуса
    valid_statuses = ["submitted", "confirmed", "cancelled", "failed"]
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

        # При необходимости сохраняем external_order_id если его ранее не было
        if external_order_id and not order.external_order_id:
            order.external_order_id = external_order_id

        # Обновляем время обновления
        order.updated_at = datetime.utcnow()

        await db.commit()
        if old_status != new_status and new_status in ["confirmed", "cancelled", "failed"]:
            await send_order_status_notification(order, old_status, new_status, db)

        logger.info(
            f"Order {order.uuid} status updated from {old_status} to {new_status} via callback"
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
            f"Failed to update order status from external callback: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to update order")


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

        # Сортируем по дате создания (новые сначала)
        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        return orders

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

        if old_status != status and status in ["confirmed", "cancelled", "failed"]:
            await send_order_status_notification(order, old_status, status, db)

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
    """Регистрация новой аптеки в системе бронирования"""
    try:
        # Проверяем существование аптеки
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == config_data.pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")

        # Проверяем, нет ли уже конфигурации для этой аптеки
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

        # Создаем конфигурацию API
        api_config = PharmacyAPIConfig(
            uuid=uuid.uuid4(),
            pharmacy_id=config_data.pharmacy_id,
            api_type=config_data.api_type,
            endpoint_url=config_data.endpoint_url,
            auth_type=config_data.auth_type,
            sync_from_date=config_data.sync_from_date,
            is_active=config_data.is_active,
        )
        api_config.set_auth_token(auth_token)

        db.add(api_config)
        await db.commit()

        return {
            "status": "success",
            "pharmacy_id": str(config_data.pharmacy_id),
            "auth_token": auth_token,  # Возвращаем только один раз!
            "message": "Keep this token secure - it won't be shown again",
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


@router.get(
    "/pharmacies/{pharmacy_id}/orders", response_model=List[BookingOrderResponse]
)
async def get_pharmacy_orders(
    pharmacy_id: uuid.UUID,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение заказов конкретной аптеки"""
    try:
        # Проверяем существование аптеки
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.uuid == pharmacy_id)
        )
        pharmacy = pharmacy_result.scalar_one_or_none()

        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")

        query = select(BookingOrder).where(BookingOrder.pharmacy_id == pharmacy_id)

        if status:
            query = query.where(BookingOrder.status == status)

        query = query.order_by(BookingOrder.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        return orders

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



async def get_user_telegram_id_by_order(order: BookingOrder, db: AsyncSession) -> Optional[int]:
    """Получить telegram_id пользователя по заказу - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        # Теперь telegram_id хранится прямо в заказе
        if order.telegram_id:
            return order.telegram_id

        logger.warning(f"No telegram_id found for order {order.uuid}")
        return None

    except Exception as e:
        logger.error(f"Error getting telegram_id for order {order.uuid}: {e}")
        return None

async def get_pharmacy_name(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить название аптеки - как в user_questions.py"""
    result = await db.execute(
        select(Pharmacy.name).where(Pharmacy.uuid == pharmacy_id)
    )
    pharmacy = result.scalar_one_or_none()
    return pharmacy.name if pharmacy else "Неизвестная аптека"

async def get_pharmacy_phone(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить телефон аптеки"""
    result = await db.execute(
        select(Pharmacy.phone).where(Pharmacy.uuid == pharmacy_id)
    )
    phone = result.scalar_one_or_none()
    return phone if phone else "Не указан"

async def get_pharmacy_address(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    """Получить адрес аптеки"""
    result = await db.execute(
        select(Pharmacy.address).where(Pharmacy.uuid == pharmacy_id)
    )
    address = result.scalar_one_or_none()
    return address if address else "Адрес не указан"

async def send_order_status_notification(order: BookingOrder, old_status: str, new_status: str, db: AsyncSession):
    """Отправка уведомления о статусе заказа в Telegram"""
    try:
        # Получаем бота как в user_questions.py
        from bot.core import bot_manager
        bot, _ = await bot_manager.initialize()

        if not bot:
            logger.error("Bot not initialized for sending order notification")
            return

        # TODO: Получить telegram_id пользователя
        telegram_id = await get_user_telegram_id_by_order(order, db)

        if not telegram_id:
            logger.warning(f"No telegram_id found for order {order.uuid}")
            return

        # Получаем информацию об аптеке
        pharmacy_name = await get_pharmacy_name(order.pharmacy_id, db)
        pharmacy_phone = await get_pharmacy_phone(order.pharmacy_id, db)

        # Форматируем сообщение как в user_questions.py
        if new_status == "confirmed":
            message_text = (
                "✅ **Ваш заказ подтвержден!**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🏪 Аптека: {pharmacy_name}\n"
                f"📍 Адрес: {await get_pharmacy_address(order.pharmacy_id, db)}\n"
                f"📞 Телефон: {pharmacy_phone}\n"
                f"Можете забирать ваш заказ! 🎉"  # Добавить эту строку
            )
        elif new_status == "cancelled":
            message_text = (
                "❌ **Ваш заказ отменен**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🏪 Аптека: {pharmacy_name}\n\n"
                "Если это ошибка, свяжитесь с аптекой по телефону выше."
            )
        elif new_status == "failed":
            message_text = (
                "⚠️ **Проблема с вашим заказом**\n\n"
                f"📦 Номер заказа: `{order.uuid}`\n"
                f"🏪 Аптека: {pharmacy_name}\n\n"
                "Техническая ошибка. Мы уже работаем над решением."
            )
        else:
            return  # Не отправляем уведомление для других статусов

        await bot.send_message(
            chat_id=telegram_id,
            text=message_text,
            parse_mode="Markdown"
        )
        logger.info(f"Order status notification sent to user {telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send order status notification: {e}")
