# booking_models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger,  Boolean, Date, ForeignKey, Numeric, DateTime,
    UniqueConstraint, Index, Text, LargeBinary, func, CheckConstraint, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Импортируем Base из base.py
from .base import Base

# booking_models.py
class BookingOrder(Base):
    __tablename__ = "booking_orders"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_order_id = Column(String(255), nullable=True, index=True)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False)

    # Изменить на nullable
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.uuid"), nullable=True)

    # Добавить кэшированные данные о продукте
    product_name = Column(String(255), nullable=True)
    product_form = Column(String(255), nullable=True)
    product_manufacturer = Column(String(255), nullable=True)
    product_country = Column(String(255), nullable=True)
    product_price = Column(Numeric(12, 2), nullable=True)
    product_serial = Column(String(255), nullable=True)

    quantity = Column(Integer, nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    scheduled_pickup = Column(DateTime(timezone=True), nullable=True)
    telegram_id = Column(BigInteger, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Добавить поля для отмены заказа
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)

    pharmacy = relationship("Pharmacy", back_populates="booking_orders", lazy="select")
    product = relationship("Product", lazy="select")

    __table_args__ = (
        Index('idx_booking_status', 'status'),
        Index('idx_booking_pharmacy', 'pharmacy_id'),
        Index('idx_booking_created', 'created_at'),
        Index('idx_booking_product_id', 'product_id'),
        CheckConstraint('quantity > 0', name='ck_booking_quantity_positive'),
    )

class PharmacyAPIConfig(Base):
    __tablename__ = "pharmacy_api_configs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False, unique=True)
    api_type = Column(String(50), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    auth_token = Column(LargeBinary, nullable=False)
    auth_type = Column(String(50), default="bearer")
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    sync_from_date = Column(DateTime(timezone=True), nullable=True)

    # Используем строковую ссылку
    pharmacy = relationship("Pharmacy", back_populates="api_config", lazy="select")

    # Методы шифрования остаются без изменений
    def set_auth_token(self, token: str):
        from cryptography.fernet import Fernet
        import os
        import logging
        logger = logging.getLogger(__name__)

        ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
        if not ENCRYPTION_KEY:
            raise RuntimeError("ENCRYPTION_KEY is not configured")

        try:
            key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
            cipher = Fernet(key)
            if isinstance(token, str):
                token_bytes = token.encode()
            else:
                token_bytes = token
            self.auth_token = cipher.encrypt(token_bytes)
        except Exception as e:
            logger.exception("Failed to encrypt auth token")
            raise

    def get_auth_token(self) -> str:
        from cryptography.fernet import Fernet, InvalidToken
        import os
        import logging
        logger = logging.getLogger(__name__)

        ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
        if not ENCRYPTION_KEY:
            raise RuntimeError("ENCRYPTION_KEY is not configured")

        try:
            if not self.auth_token:
                return ""
            key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
            cipher = Fernet(key)
            decrypted = cipher.decrypt(self.auth_token)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encryption token or key mismatch")
            return ""
        except Exception as e:
            logger.error(f"Failed to decrypt auth token: {e}")
            return ""

class SyncLog(Base):
    __tablename__ = "sync_logs"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False)
    sync_type = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="running")
    records_processed = Column(Integer, default=0)
    details = Column(Text, nullable=True)

    pharmacy = relationship("Pharmacy", lazy="select")
