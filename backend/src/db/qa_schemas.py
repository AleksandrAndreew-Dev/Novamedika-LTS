from pydantic import BaseModel
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

class PharmacistBase(BaseModel):
    pharmacy_info: Dict[str, Any]

class PharmacistCreate(PharmacistBase):
    user_data: UserBase



class PharmacyInfoSimple(BaseModel):
    name: str
    number: str
    city: str
    chain: str

    
class PharmacistResponse(BaseModel):
    uuid: uuid.UUID
    user: UserResponse
    pharmacy_info: PharmacyInfoSimple  # ✅ Заменяем PharmacyRead
    is_active: bool

    model_config = {"from_attributes": True}

class QuestionBase(BaseModel):
    text: str
    category: str = "general"
    context_data: Optional[Dict[str, Any]] = None

class QuestionCreate(QuestionBase):
    telegram_user_id: int

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

    model_config = {"from_attributes": True}

class AnswerBase(BaseModel):
    text: str

class AnswerCreate(AnswerBase):
    question_id: uuid.UUID

class AnswerResponse(BaseModel):
    uuid: uuid.UUID
    text: str
    created_at: datetime
    pharmacist: PharmacistResponse

    model_config = {"from_attributes": True}



