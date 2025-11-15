import uuid
from sqlalchemy import Column, String, Date, ForeignKey, Numeric, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.database import Base  # ваш declarative_base()

class Pharmacy(Base):
    __tablename__ = "pharmacies"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(30), nullable=False)
    pharmacy_number = Column(String(100), nullable=False)
    city = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    opening_hours = Column(String(255), nullable=True)

    # Добавляем уникальное ограничение
    __table_args__ = (
        UniqueConstraint('name', 'pharmacy_number', name='uq_pharmacy_name_number'),
    )

    products = relationship("Product", back_populates="pharmacy")


# models.py - обновите модель Product
class Product(Base):
    __tablename__ = "products"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    form = Column(String(255), nullable=False, default="-")
    manufacturer = Column(String(255), nullable=False, default="")
    country = Column(String(255), nullable=False, default="")
    serial = Column(String(255), nullable=False, default="")
    price = Column(Numeric(12, 2), default=0.0)  # Увеличено с 10 до 12
    quantity = Column(Numeric(12, 3), nullable=False, default=0.0)  # Увеличено с 10 до 12
    total_price = Column(Numeric(12, 2), default=0.0)  # Увеличено с 10 до 12
    expiry_date = Column(Date, nullable=False)
    category = Column(String(255), nullable=False, default="")
    import_date = Column(Date, nullable=True)
    internal_code = Column(String(255), nullable=True)
    wholesale_price = Column(Numeric(12, 2), nullable=False, default=0.0)  # Увеличено с 10 до 12
    retail_price = Column(Numeric(12, 2), default=0.0)  # Увеличено с 10 до 12
    distributor = Column(String(255), nullable=False, default="")
    internal_id = Column(String(255), nullable=False, default="")
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    pharmacy = relationship("Pharmacy", back_populates="products")
