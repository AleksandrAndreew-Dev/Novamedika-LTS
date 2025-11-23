import uuid
from sqlalchemy import Column, String, Date, ForeignKey, Numeric, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.database import Base
from utils.time_utils import get_utc_now_naive

class Pharmacy(Base):
    __tablename__ = "pharmacies"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(30), nullable=False)
    pharmacy_number = Column(String(100), nullable=False)
    city = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    opening_hours = Column(String(255), nullable=True)
    chain = Column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', 'pharmacy_number', name='uq_pharmacy_name_number'),
    )

    products = relationship("Product", back_populates="pharmacy")

    # ДОБАВИТЬ обратные relationships:
    booking_orders = relationship("BookingOrder", back_populates="pharmacy")
    api_config = relationship("PharmacyAPIConfig", back_populates="pharmacy", uselist=False)


# models.py - обновите модель Product
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
    updated_at = Column(DateTime, default=get_utc_now_naive, onupdate=get_utc_now_naive)

    # ДОБАВИТЬ если нужно:
    # external_id = Column(String(255), nullable=True)  # для синхронизации

    search_vector = Column(TSVECTOR, nullable=True)

    # ОДИН relationship:
    pharmacy = relationship("Pharmacy", back_populates="products")

    __table_args__ = (
        Index('idx_product_search_vector', 'search_vector', postgresql_using='gin'),
        Index('idx_product_name_gin', 'name', postgresql_using='gin'),
        Index('idx_product_manufacturer', 'manufacturer'),
        Index('idx_product_form', 'form'),
        Index('idx_product_price', 'price'),
    )
