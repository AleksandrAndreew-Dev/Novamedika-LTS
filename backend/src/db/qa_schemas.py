# db/qa_schemas.py
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid


class UserBase(BaseModel):
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telegram_username: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    uuid: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# Обновленная схема информации об аптеке
class PharmacyInfoSimple(BaseModel):
    name: str
    number: str
    city: Optional[str] = ""
    chain: str
    role: str

    model_config = {"from_attributes": True}


class PharmacistBase(BaseModel):
    pharmacy_info: Dict[str, Any]


class PharmacistCreate(PharmacistBase):
    user_data: UserBase


class PharmacistResponse(BaseModel):
    uuid: uuid.UUID
    user: UserResponse
    pharmacy_info: PharmacyInfoSimple
    is_active: bool

    model_config = {"from_attributes": True}


class QuestionBase(BaseModel):
    text: str
    category: str = "general"
    context_data: Optional[Dict[str, Any]] = None


class QuestionCreate(QuestionBase):
    telegram_user_id: int


class AnswerResponse(BaseModel):
    uuid: uuid.UUID
    text: str
    created_at: datetime
    pharmacist: PharmacistResponse

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    uuid: uuid.UUID
    text: str
    status: str
    category: str
    created_at: datetime
    user: UserResponse
    context_data: Optional[Dict[str, Any]]
    assigned_to: Optional[PharmacistResponse] = None
    answered_by: Optional[PharmacistResponse] = None
    answers: List[AnswerResponse] = []

    # Валидатор для обработки UUID вместо полного объекта
    # Если пришел только UUID без связанных данных - возвращаем None
    @field_validator("assigned_to", "answered_by", mode="before")
    @classmethod
    def validate_pharmacist_uuid(cls, v):
        if v is None:
            return None
        # Если значение - UUID (строка или объект), возвращаем None
        # Фронтенд должен загрузить детали отдельным запросом
        if isinstance(v, (str, uuid.UUID)):
            return None
        return v

    model_config = {"from_attributes": True}


class AnswerBase(BaseModel):
    text: str


class AnswerCreate(AnswerBase):
    question_id: uuid.UUID
