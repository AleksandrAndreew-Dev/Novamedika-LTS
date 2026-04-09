"""Вспомогательные функции для роутеров заказов."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.booking_models import BookingOrder, PharmacyAPIConfig
from db.qa_models import User
from db.models import Pharmacy
from utils.send_sms import send_a1_sms

logger = logging.getLogger(__name__)


async def authenticate_pharmacy_api_config(
    db: AsyncSession, token: str
) -> PharmacyAPIConfig:
    """Найти активную конфигурацию аптеки по токену."""
    config_result = await db.execute(
        select(PharmacyAPIConfig).where(PharmacyAPIConfig.is_active == True)
    )
    configs = config_result.scalars().all()

    for config in configs:
        try:
            if config.get_auth_token() == token:
                return config
        except Exception as e:
            logger.warning(f"Error decrypting token for config {config.uuid}: {e}")
            continue

    raise Exception("Invalid or inactive token")


async def get_user_telegram_id_by_order(
    order: BookingOrder, db: AsyncSession
) -> str | None:
    """Получить telegram_id пользователя по заказу."""
    if order.telegram_id:
        return order.telegram_id

    user_result = await db.execute(
        select(User).where(User.uuid == order.customer_phone)
    )
    user = user_result.scalar_one_or_none()
    return str(user.telegram_id) if user and user.telegram_id else None


async def get_pharmacy_name(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()
    return pharmacy.name if pharmacy else "Неизвестная аптека"


async def get_pharmacy_phone(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()
    return pharmacy.phone if pharmacy else ""


async def get_pharmacy_address(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()
    return pharmacy.address if pharmacy else ""


async def get_product_name(product_id: uuid.UUID, db: AsyncSession) -> str:
    from db.models import Product

    result = await db.execute(select(Product).where(Product.uuid == product_id))
    product = result.scalar_one_or_none()
    return product.name if product else ""


async def get_pharmacy_number(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()
    return pharmacy.pharmacy_number if pharmacy else ""


async def get_pharmacy_opening_hours(pharmacy_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(Pharmacy).where(Pharmacy.uuid == pharmacy_id))
    pharmacy = result.scalar_one_or_none()
    return pharmacy.opening_hours if pharmacy else ""


async def send_order_status_notification(
    order: BookingOrder,
    old_status: str,
    new_status: str,
    db: AsyncSession,
    reason: str = "",
):
    """Отправить уведомление пользователю об изменении статуса заказа."""
    telegram_id = await get_user_telegram_id_by_order(order, db)
    if not telegram_id:
        logger.warning(f"No telegram_id for order {order.uuid}")
        return

    status_emoji = {
        "pending": "⏳",
        "submitted": "📤",
        "confirmed": "✅",
        "cancelled": "❌",
        "failed": "⚠️",
    }

    status_text_ru = {
        "pending": "ожидает",
        "submitted": "отправлен",
        "confirmed": "подтверждён",
        "cancelled": "отменён",
        "failed": "не выполнен",
    }

    pharmacy_name = await get_pharmacy_name(order.pharmacy_id, db)
    product_name = order.product_name or await get_product_name(order.product_id, db)
    pharmacy_phone = await get_pharmacy_phone(order.pharmacy_id, db)
    pharmacy_address = await get_pharmacy_address(order.pharmacy_id, db)

    emoji = status_emoji.get(new_status, "🔄")
    text_ru = status_text_ru.get(new_status, new_status)

    notification = (
        f"{emoji} <b>Статус заказа изменён</b>\n\n"
        f"💊 {product_name}\n"
        f"🏥 {pharmacy_name}\n"
        f"📞 {pharmacy_phone}\n"
        f"📍 {pharmacy_address}\n\n"
        f"Новый статус: <b>{text_ru}</b>"
    )

    if reason:
        notification += f"\n\n💬 Комментарий: {reason}"

    if new_status == "confirmed":
        notification += "\n\nВы можете забрать заказ в аптеке."

    try:
        from bot.core import bot_manager

        bot, _ = await bot_manager.initialize()
        if bot:
            await bot.send_message(
                chat_id=telegram_id, text=notification, parse_mode="HTML"
            )
            logger.info(
                f"Sent Telegram notification for order {order.uuid}: {old_status} → {new_status}"
            )
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

    # SMS как fallback
    if new_status == "confirmed":
        try:
            sms_text = (
                f"Ваш заказ {product_name} подтверждён. "
                f"Заберите в {pharmacy_name}. Тел: {pharmacy_phone}"
            )
            await send_a1_sms(telegram_id, sms_text)
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
