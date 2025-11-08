from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
import uuid


class ProductBase(BaseModel):
    name: str
    form: str
    manufacturer: str
    country: str
    serial: str
    price: float
    quantity: float
    total_price: float
    expiry_date: date  # Теперь обязательно
    category: str
    import_date: Optional[date] = None
    internal_code: Optional[str] = None
    wholesale_price: float
    retail_price: float
    distributor: str
    internal_id: str


class ProductCreate(ProductBase):
    pharmacy_id: uuid.UUID


class ProductRead(ProductBase):
    uuid: uuid.UUID
    updated_at: datetime

    class Config:
        orm_mode = True


class PharmacyBase(BaseModel):
    name: Optional[str] = None
    pharmacy_number: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    opening_hours: Optional[str] = None


class PharmacyCreate(PharmacyBase):
    pass


class PharmacyRead(PharmacyBase):
    uuid: uuid.UUID
    products: List[ProductRead] = []

    class Config:
        orm_mode = True
