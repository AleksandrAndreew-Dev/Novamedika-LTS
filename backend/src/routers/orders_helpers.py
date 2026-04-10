"""Вспомогательные функции для роутеров заказов."""

import logging
import uuid
from datetime import datetime, timedelta

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
    # 1. Пробуем получить telegram_id напрямую из заказа
    if order.telegram_id:
        return str(order.telegram_id)

    # 2. Ищем по номеру телефона в таблице пользователей
    if order.customer_phone:
        user_result = await db.execute(
            select(User).where(User.phone == order.customer_phone)
        )
        user = user_result.scalar_one_or_none()
        if user and user.telegram_id:
            return str(user.telegram_id)

    return None


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
    product_name = order.product_name or await get_product_name(order.product_id, db)
    pharmacy_name = await get_pharmacy_name(order.pharmacy_id, db)
    pharmacy_number = await get_pharmacy_number(order.pharmacy_id, db)
    pharmacy_phone = await get_pharmacy_phone(order.pharmacy_id, db)
    pharmacy_address = await get_pharmacy_address(order.pharmacy_id, db)
    pharmacy_opening_hours = await get_pharmacy_opening_hours(order.pharmacy_id, db)

    pharmacy_full_name = pharmacy_name
    if pharmacy_number:
        pharmacy_full_name += f" №{pharmacy_number}"

    # Формируем полное сообщение
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

    emoji = status_emoji.get(new_status, "🔄")
    text_ru = status_text_ru.get(new_status, new_status)

    if new_status == "confirmed":
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%d.%m.%Y")

        notification = (
            f"✅ <b>Ваш заказ подтверждён!</b>\n\n"
            f"📦 Номер заказа: <code>{order.uuid}</code>\n"
            f"🛍️ Товар: {product_name}\n"
            f"🏪 Аптека: {pharmacy_full_name}\n"
            f"📍 Адрес: {pharmacy_address}\n"
            f"📞 Телефон: {pharmacy_phone}\n"
            f"🕐 Время работы: {pharmacy_opening_hours}\n\n"
        )
        if reason:
            notification += f"📝 <b>Комментарий от аптеки:</b> {reason}\n\n"
        notification += f"Вы можете забрать заказ до 12:00 {tomorrow_str}. 🎉"

        sms_text = (
            f"Заказ подтверждён. {product_name}. Ждём до 12:00 {tomorrow_str}. "
            f"Адрес: {pharmacy_address}. Аптека: {pharmacy_full_name}. Тел: {pharmacy_phone}"
        )

    elif new_status == "cancelled":
        cancellation_reason = reason or order.cancellation_reason or "не указана"
        notification = (
            f"❌ <b>Ваш заказ отменён</b>\n\n"
            f"📦 Номер заказа: <code>{order.uuid}</code>\n"
            f"🛍️ Товар: {product_name}\n"
            f"🏪 Аптека: {pharmacy_full_name}\n"
            f"📍 Адрес: {pharmacy_address}\n"
            f"📞 Телефон: {pharmacy_phone}\n"
            f"🕐 Время работы: {pharmacy_opening_hours}\n\n"
        )
        if reason:
            notification += f"📝 <b>Причина отмены:</b> {reason}\n\n"
        notification += "Если это ошибка, свяжитесь с аптекой по телефону выше."

        sms_text = (
            f"Заказ отменён. {product_name}. Аптека: {pharmacy_full_name}. "
            f"Тел: {pharmacy_phone}. Причина: {cancellation_reason}"
        )

    elif new_status == "failed":
        notification = (
            f"⚠️ <b>Проблема с вашим заказом</b>\n\n"
            f"📦 Номер заказа: <code>{order.uuid}</code>\n"
            f"🛍️ Товар: {product_name}\n"
            f"🏪 Аптека: {pharmacy_full_name}\n"
            f"📍 Адрес: {pharmacy_address}\n"
            f"📞 Телефон: {pharmacy_phone}\n"
            f"🕐 Время работы: {pharmacy_opening_hours}\n\n"
        )
        if reason:
            notification += f"📝 <b>Причина проблемы:</b> {reason}\n\n"
        notification += (
            "Техническая ошибка при обработке заказа. Мы уже работаем над решением."
        )

        sms_text = (
            f"Проблема с заказом. Мы свяжемся с вами. Тел. аптеки: {pharmacy_phone}"
        )
    else:
        return  # Не отправляем уведомление для других статусов

    # Отправляем через Telegram
    if telegram_id:
        try:
            from bot.core import bot_manager

            bot, _ = await bot_manager.initialize()
            if bot:
                await bot.send_message(
                    chat_id=int(telegram_id), text=notification, parse_mode="HTML"
                )
                logger.info(
                    f"Sent Telegram notification for order {order.uuid}: {old_status} → {new_status}"
                )
                return
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    # SMS как fallback
    if order.customer_phone:
        try:
            await send_a1_sms(order.customer_phone, sms_text)
            logger.info(
                f"Sent SMS notification for order {order.uuid} to {order.customer_phone}"
            )
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
    else:
        logger.warning(f"No contact method for order {order.uuid}")
