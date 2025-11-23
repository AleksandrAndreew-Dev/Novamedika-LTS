import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from db.database import async_session_maker
from db.booking_models import PharmacyAPIConfig, BookingOrder, SyncLog, Product
from order_manager.manager import ExternalAPIManager

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        self.api_manager = ExternalAPIManager()

    async def sync_all_pharmacies_orders(self):
        """Синхронизация заказов для всех активных аптек"""
        async with async_session_maker() as session:
            configs_result = await session.execute(
                select(PharmacyAPIConfig).where(PharmacyAPIConfig.is_active == True)
            )
            configs = configs_result.scalars().all()

            for config in configs:
                # Обрабатываем каждую конфигурацию последовательно (можно параллелить при необходимости)
                await self.sync_pharmacy_orders(session, config)

    async def sync_pharmacy_orders(self, session: AsyncSession, api_config: PharmacyAPIConfig):
        """Синхронизация заказов для конкретной аптеки"""
        sync_log = SyncLog(
            uuid=uuid.uuid4(),
            pharmacy_id=api_config.pharmacy_id,
            sync_type="orders",
            status="running",
            records_processed=0
        )
        session.add(sync_log)
        await session.flush()  # чтобы sync_log.uuid был доступен

        try:
            # Определяем время последней синхронизации
            since = api_config.last_sync_at or api_config.sync_from_date

            # Получаем заказы из внешнего API
            external_orders = await self.api_manager.sync_orders_from_pharmacy(api_config, since)

            processed = 0
            for ext_order in external_orders:
                ext_id = ext_order.get("id") or ext_order.get("external_order_id") or ext_order.get("order_id")
                if not ext_id:
                    logger.warning("External order without id skipped")
                    continue

                # Проверяем наличие по external_order_id и pharmacy_id
                existing_result = await session.execute(
                    select(BookingOrder).where(
                        BookingOrder.external_order_id == ext_id,
                        BookingOrder.pharmacy_id == api_config.pharmacy_id
                    )
                )
                if existing_result.scalar_one_or_none():
                    # уже есть — пропускаем
                    continue

                # Создаём заказ в сессии (не коммитим сразу, соберём пакет)
                order = await self.create_order_from_external(session, api_config.pharmacy_id, ext_order)
                if order:
                    processed += 1

            # Обновляем время и лог синка
            api_config.last_sync_at = datetime.utcnow()
            sync_log.status = "success"
            sync_log.records_processed = processed
            sync_log.finished_at = datetime.utcnow()

            await session.commit()
            logger.info(f"Synced {processed} orders for pharmacy {api_config.pharmacy_id}")

        except Exception as e:
            # На ошибке помечаем лог и фиксируем время
            try:
                sync_log.status = "failed"
                sync_log.details = str(e)
                sync_log.finished_at = datetime.utcnow()
                await session.commit()
            except Exception:
                logger.exception("Failed to persist sync_log after error")
            logger.exception(f"Sync failed for pharmacy {api_config.pharmacy_id}: {str(e)}")

    async def create_order_from_external(self, session: AsyncSession, pharmacy_id: str, ext_order: dict):
        """Создание заказа из внешних данных. НЕ сохраняем email."""
        try:
            # Нормализация полей внешнего заказа
            ext_id = ext_order.get("id") or ext_order.get("external_order_id") or ext_order.get("order_id")
            quantity = int(ext_order.get("quantity", 1) or 1)

            # scheduled_pickup может быть строкой ISO — пробуем распарсить
            scheduled_raw = ext_order.get("scheduled_pickup")
            scheduled = None
            if scheduled_raw:
                try:
                    # если это уже datetime — оставить
                    if isinstance(scheduled_raw, datetime):
                        scheduled = scheduled_raw
                    else:
                        scheduled = datetime.fromisoformat(str(scheduled_raw))
                except Exception:
                    logger.warning(f"Unable to parse scheduled_pickup: {scheduled_raw}")
                    scheduled = None

            # Получаем или создаём продукт, возвращаем UUID продукта
            product_uuid = await self.get_or_create_product(session, ext_order)
            if not product_uuid:
                logger.warning("Product resolution failed for external order; skipping order creation")
                return None

            order = BookingOrder(
                uuid=uuid.uuid4(),
                pharmacy_id=pharmacy_id,
                external_order_id=str(ext_id),
                product_id=product_uuid,
                quantity=quantity,
                customer_name=ext_order.get("customer_name", "") or "",
                customer_phone=ext_order.get("customer_phone", "") or "",
                status=ext_order.get("status", "pending"),
                scheduled_pickup=scheduled
            )

            session.add(order)
            # не делаем commit здесь; коммит выполняется в sync_pharmacy_orders после обработки всех записей
            return order

        except Exception as e:
            logger.exception(f"Error creating order from external data: {str(e)}")
            return None

    async def get_or_create_product(self, session: AsyncSession, ext_order: dict):
        """
        Найти продукт по внешним данным или создать новый.
        Возвращает UUID продукта (as uuid.UUID or str), либо None при ошибке.
        Пример логики (адаптируй под свою модель Product):
          - пробуем найти по external_id/internal_code
          - затем по name + manufacturer + serial + expiry_date
          - при отсутствии — создаём новый продукт
        """
        try:
            # Попытка найти по внешнему идентификатору продукта (если есть)
            ext_product_id = ext_order.get("product_external_id") or ext_order.get("product_id")
            if ext_product_id:
    # Искать по internal_id или другим существующим полям
                result = await session.execute(
                    select(Product).where(
                        (Product.internal_id == str(ext_product_id)) |
                        (Product.internal_code == str(ext_product_id))
                    )
                )
                prod = result.scalar_one_or_none()
                if prod:
                    return prod.uuid

            # Поиск по имени и дополнительным признакам
            name = ext_order.get("product_name") or ext_order.get("name")
            serial = ext_order.get("serial") or ""
            expiry = ext_order.get("expiry_date")
            expiry_date = None
            if expiry:
                try:
                    if isinstance(expiry, str):
                        expiry_date = datetime.fromisoformat(expiry).date()
                    elif isinstance(expiry, datetime):
                        expiry_date = expiry.date()
                except Exception:
                    expiry_date = None

            if name:
                q = select(Product).where(
                    Product.name == name,
                    Product.pharmacy_id == ext_order.get("pharmacy_id") or None
                )
                result = await session.execute(q)
                prod = result.scalar_one_or_none()
                if prod:
                    return prod.uuid

            # Если не найден — создаём новый продукт минимальным набором полей
            new_prod = Product(
                uuid=uuid.uuid4(),
                name=name or "unknown",
                form=ext_order.get("form") or "-",
                manufacturer=ext_order.get("manufacturer") or "",
                country=ext_order.get("country") or "",
                serial=serial,
                expiry_date=expiry_date,
                pharmacy_id=ext_order.get("pharmacy_id") or None
            )
            session.add(new_prod)
            await session.flush()  # чтобы получить uuid в рамках сессии
            return new_prod.uuid

        except Exception as e:
            logger.exception(f"Error in get_or_create_product: {str(e)}")
            return None
