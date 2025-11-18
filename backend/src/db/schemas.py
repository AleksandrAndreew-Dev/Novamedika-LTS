from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Dict, Any
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


class PharmacyRead(BaseModel):
    uuid: uuid.UUID
    name: str
    pharmacy_number: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    chain: str  # Добавьте это поле

    class Config:
        from_attributes = True


class PharmacyInfo(BaseModel):
    pharmacy_name: str
    pharmacy_number: str
    pharmacy_city: str
    pharmacy_address: str
    pharmacy_phone: str


class GroupedProductResponse(BaseModel):
    name: str
    form: str
    pharmacy_name: str
    pharmacy_city: str
    pharmacy_address: str
    pharmacy_phone: str
    pharmacy_number: str
    price: float
    quantity: float
    manufacturer: str
    country: str
    pharmacies: List[PharmacyInfo]
    updated_at: datetime


class SearchResponse(BaseModel):
    items: List[GroupedProductResponse]
    total: int
    page: int
    size: int
    unique_cities: List[str]
    unique_forms: List[str]
    filters: Dict[str, Any]


# schemas.py - дополнить
class ProductPreview(BaseModel):
    name: str
    form: str
    manufacturer: str
    country: str
    price: float
    pharmacy_city: str

class TwoStepSearchResponse(BaseModel):
    available_forms: List[str]
    preview_products: List[ProductPreview]
    total_found: int
    filters: dict


class PharmacyUpdate(BaseModel):
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    opening_hours: Optional[str] = None

class PharmacyResponse(BaseModel):
    uuid: uuid.UUID
    name: str
    pharmacy_number: str
    city: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    opening_hours: Optional[str]
    chain: str

    class Config:
        from_attributes = True
