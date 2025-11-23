# db/booking_models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, ForeignKey, Numeric, DateTime,
    UniqueConstraint, Index, Text, LargeBinary, func, CheckConstraint, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from db.database import Base
from db.models import Pharmacy, Product

from cryptography.fernet import Fernet, InvalidToken
import os
import logging

logger = logging.getLogger(__name__)

# Получение ключа шифрования из безопасного источника окружения/секретного хранилища
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

def _get_cipher():
    if not ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    try:
        key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
        return Fernet(key)
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY: {e}")
        raise

def get_server_now():
    """Return SQL expression for server now (timezone aware)."""
    return func.now()


class BookingOrder(Base):
    __tablename__ = "booking_orders"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_order_id = Column(String(255), nullable=True, index=True)  # убрали global unique
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.uuid"), nullable=False)
    quantity = Column(Integer, nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # consider replacing with Enum
    scheduled_pickup = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=get_server_now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=get_server_now(), onupdate=get_server_now(), nullable=False)

    # Relationships
    pharmacy = relationship("Pharmacy", back_populates="booking_orders")
    product = relationship("Product")

    __table_args__ = (
        Index('idx_booking_status', 'status'),
        Index('idx_booking_pharmacy', 'pharmacy_id'),
        Index('idx_booking_created', 'created_at'),
        # можно добавить проверку количества > 0
        CheckConstraint('quantity > 0', name='ck_booking_quantity_positive'),
    )


class PharmacyAPIConfig(Base):
    __tablename__ = "pharmacy_api_configs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False, unique=True)
    api_type = Column(String(50), nullable=False)  # json, xml, rest, soap
    endpoint_url = Column(String(500), nullable=False)
    auth_token = Column(LargeBinary, nullable=False)  # теперь binary (шифртекст)
    auth_type = Column(String(50), default="bearer")  # bearer, api_key, basic
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    sync_from_date = Column(DateTime(timezone=True), nullable=True)  # Начальная дата синхронизации

    pharmacy = relationship("Pharmacy", back_populates="api_config")

    # Методы шифрования/дешифровки токена
    def set_auth_token(self, token: str):
        """Шифрует и сохраняет токен. token: str"""
        try:
            cipher = _get_cipher()
            if isinstance(token, str):
                token_bytes = token.encode()
            else:
                token_bytes = token
            self.auth_token = cipher.encrypt(token_bytes)
        except Exception as e:
            logger.exception("Failed to encrypt auth token")
            raise

    def get_auth_token(self) -> str:
        """Дешифрует и возвращает токен как строку"""
        try:
            if not self.auth_token:
                return ""
            cipher = _get_cipher()
            decrypted = cipher.decrypt(self.auth_token)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encryption token or key mismatch")
            return ""  # или raise специальное исключение
        except Exception as e:
            logger.error(f"Failed to decrypt auth token: {e}")
            return ""


class SyncLog(Base):
    __tablename__ = "sync_logs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False)
    sync_type = Column(String(50), nullable=False)  # orders, products, inventory
    started_at = Column(DateTime(timezone=True), server_default=get_server_now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="running")  # running, success, failed
    records_processed = Column(Integer, default=0)
    details = Column(Text, nullable=True)

    pharmacy = relationship("Pharmacy")
