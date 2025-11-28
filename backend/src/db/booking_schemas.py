from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import uuid


class BookingOrderBase(BaseModel):
    product_id: uuid.UUID
    quantity: int
    customer_name: str
    customer_phone: str
    scheduled_pickup: Optional[datetime] = None
    telegram_id: Optional[int] = None  # Добавляем поле для Telegram ID

    model_config = {"from_attributes": True}

    # Пример валидации количества
    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v):
        # Приводим строку к int, проверяем минимальное значение
        try:
            val = int(v)
        except Exception:
            raise ValueError("quantity must be an integer")
        if val <= 0:
            raise ValueError("quantity must be > 0")
        return val

    # Пример валидации телефона (минимальная демонстрация)
    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str):
        phone = v.strip()
        if not phone:
            raise ValueError("customer_phone is required")
        # Простая проверка: оставляем цифры и плюс
        cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if len([c for c in cleaned if c.isdigit()]) < 11:
            raise ValueError("customer_phone seems too short")
        return phone


class BookingOrderCreate(BookingOrderBase):
    pharmacy_id: uuid.UUID


class BookingOrderResponse(BookingOrderBase):
    uuid: uuid.UUID
    pharmacy_id: uuid.UUID
    status: str
    external_order_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PharmacyAPIConfigBase(BaseModel):
    api_type: str
    endpoint_url: str
    auth_type: str = "bearer"
    sync_from_date: Optional[datetime] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class PharmacyAPIConfigCreate(PharmacyAPIConfigBase):
    auth_token: str
    pharmacy_id: uuid.UUID


class PharmacyAPIConfigResponse(PharmacyAPIConfigBase):
    uuid: uuid.UUID
    pharmacy_id: uuid.UUID
    last_sync_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SyncLogResponse(BaseModel):
    uuid: uuid.UUID
    pharmacy_id: uuid.UUID
    sync_type: str
    status: str
    records_processed: int
    started_at: datetime
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PharmacyCreate(BaseModel):
    name: str
    pharmacy_number: str
    chain: str
    city: str
    address: str
    phone: str
    opening_hours: str

class PharmacyResponse(BaseModel):
    uuid: uuid.UUID
    name: str
    pharmacy_number: str
    chain: str
    city: str
    address: str
    phone: str
    opening_hours: str

    model_config = {"from_attributes": True}
