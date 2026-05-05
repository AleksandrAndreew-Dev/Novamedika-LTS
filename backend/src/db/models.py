# db/models.py
import uuid
from sqlalchemy import (
    Column,
    String,
    Date,
    ForeignKey,
    Numeric,
    DateTime,
    UniqueConstraint,
    Index,
    Boolean,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship

from .base import Base


class AuditLog(Base):
    """Модель для аудита доступа к персональным данным (требование ОАЦ)"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Кто выполнил действие
    user_id = Column(UUID(as_uuid=True), nullable=True)  # ID пользователя (если авторизован)
    user_type = Column(String(20), nullable=False)  # 'user', 'pharmacist', 'admin', 'system'
    
    # Какое действие выполнено
    action = Column(String(50), nullable=False)  # 'read', 'create', 'update', 'delete', 'export'
    resource_type = Column(String(50), nullable=False)  # 'user', 'pharmacist', 'question', 'order'
    resource_id = Column(UUID(as_uuid=True), nullable=True)  # ID затронутого ресурса
    
    # Детали действия
    ip_address = Column(String(45), nullable=True)  # IPv4 или IPv6
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    endpoint = Column(String(255), nullable=True)  # URL endpoint
    
    # Результат
    status_code = Column(String(3), nullable=True)  # HTTP status code
    success = Column(Boolean, default=True)
    
    # Дополнительные данные (JSON для гибкости)
    details = Column(JSON, nullable=True)  # Дополнительная информация о действии
    
    # Временные метки
    created_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created_at", "created_at"),
    )


class Pharmacy(Base):
    __tablename__ = "pharmacies"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(30), nullable=False)
    pharmacy_number = Column(String(100), nullable=False)
    city = Column(String(30), nullable=True)
    district = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    opening_hours = Column(String(500), nullable=True)
    chain = Column(String(50), nullable=False)

    # Use string references to avoid circular imports
    products = relationship("Product", back_populates="pharmacy", lazy="select")
    booking_orders = relationship(
        "BookingOrder", back_populates="pharmacy", cascade="all, delete-orphan"
    )
    api_config = relationship(
        "PharmacyAPIConfig",
        back_populates="pharmacy",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("name", "pharmacy_number", name="uq_pharmacy_name_number"),
    )


# db/models.py
class Product(Base):
    __tablename__ = "products"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    form = Column(String(255), nullable=False, default="-")
    manufacturer = Column(String(255), nullable=False, default="")
    country = Column(String(255), nullable=False, default="")
    serial = Column(String(255), nullable=False, default="")
    price = Column(Numeric(12, 2), default=0.0)
    quantity = Column(Numeric(12, 3), nullable=False, default=0.0)
    total_price = Column(Numeric(12, 2), default=0.0)
    expiry_date = Column(Date, nullable=False)
    category = Column(String(255), nullable=False, default="")
    import_date = Column(Date, nullable=True)
    internal_code = Column(String(255), nullable=True)
    wholesale_price = Column(Numeric(12, 2), nullable=False, default=0.0)
    retail_price = Column(Numeric(12, 2), default=0.0)
    distributor = Column(String(255), nullable=False, default="")
    internal_id = Column(String(255), nullable=False, default="")
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), index=True)
    updated_at = Column(DateTime, nullable=False)

    # Добавить для мягкого удаления
    is_removed = Column(Boolean, default=False, nullable=False)
    removed_at = Column(DateTime, nullable=True)

    search_vector = Column(TSVECTOR, nullable=True)

    pharmacy = relationship("Pharmacy", back_populates="products", lazy="select")

    __table_args__ = (
        Index("idx_product_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_product_name_gin", "name", postgresql_using="gin"),
        Index("idx_product_manufacturer", "manufacturer"),
        Index("idx_product_form", "form"),
        Index("idx_product_price", "price"),
        Index("idx_product_is_removed", "is_removed"),  # Добавить индекс
    )
