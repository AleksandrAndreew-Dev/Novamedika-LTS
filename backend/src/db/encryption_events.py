"""Event listeners для автоматического шифрования персональных данных."""

from sqlalchemy import event
import logging

from .qa_models import User
from .booking_models import BookingOrder

logger = logging.getLogger(__name__)


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def encrypt_user_data(mapper, connection, target):
    """
    Автоматически шифровать telegram_id и phone перед сохранением в БД.
    
    Вызывается автоматически SQLAlchemy при INSERT или UPDATE записи User.
    """
    try:
        # Шифруем telegram_id если он есть и еще не зашифрован
        if hasattr(target, 'telegram_id') and target.telegram_id is not None:
            # Проверяем, нужно ли шифровать (если encrypted поле пусто)
            if not target.telegram_id_encrypted:
                logger.debug(f"Encrypting telegram_id for user {target.uuid}")
                target.set_telegram_id(target.telegram_id)
        
        # Шифруем phone если он есть и еще не зашифрован
        if hasattr(target, 'phone') and target.phone is not None:
            if not target.phone_encrypted:
                logger.debug(f"Encrypting phone for user {target.uuid}")
                target.set_phone(target.phone)
                
    except Exception as e:
        logger.error(f"Error encrypting user data: {e}", exc_info=True)
        # Не прерываем операцию, данные сохранятся в незашифрованном виде
        # Это позволит диагностировать проблему позже


@event.listens_for(BookingOrder, "before_insert")
@event.listens_for(BookingOrder, "before_update")
def encrypt_booking_data(mapper, connection, target):
    """
    Автоматически шифровать customer_phone и telegram_id перед сохранением в БД.
    
    Вызывается автоматически SQLAlchemy при INSERT или UPDATE записи BookingOrder.
    """
    try:
        # Шифруем customer_phone если он есть и еще не зашифрован
        if hasattr(target, 'customer_phone') and target.customer_phone is not None:
            if not target.customer_phone_encrypted:
                logger.debug(f"Encrypting customer_phone for order {target.uuid}")
                target.set_customer_phone(target.customer_phone)
        
        # Шифруем telegram_id если он есть и еще не зашифрован
        if hasattr(target, 'telegram_id') and target.telegram_id is not None:
            if not target.telegram_id_encrypted:
                logger.debug(f"Encrypting telegram_id for order {target.uuid}")
                target.set_telegram_id(target.telegram_id)
                
    except Exception as e:
        logger.error(f"Error encrypting booking data: {e}", exc_info=True)
        # Не прерываем операцию, данные сохранятся в незашифрованном виде


# Регистрация event listeners происходит автоматически при импорте этого модуля
logger.info("Encryption event listeners registered successfully")
