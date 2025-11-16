from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import uuid

from db.schemas import PharmacyRead

class QuestionBase(BaseModel):
    text: str
    parent_question_id: Optional[uuid.UUID] = None

class QuestionCreate(QuestionBase):
    telegram_user_id: int

class AnswerBase(BaseModel):
    text: str

class AnswerCreate(AnswerBase):
    question_id: uuid.UUID


class UserResponse(BaseModel):
    uuid: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telegram_username: Optional[str] = None

    class Config:
        from_attributes = True

class PharmacistBasicResponse(BaseModel):
    uuid: uuid.UUID
    user: UserResponse

    class Config:
        from_attributes = True

class AnswerResponse(BaseModel):
    uuid: uuid.UUID
    text: str
    created_at: datetime
    pharmacist: PharmacistBasicResponse

    class Config:
        from_attributes = True

class QuestionResponse(BaseModel):
    uuid: uuid.UUID
    text: str
    status: str
    created_at: datetime
    user: UserResponse
    assigned_to: Optional[PharmacistBasicResponse] = None
    answered_by: Optional[PharmacistBasicResponse] = None
    answers: List[AnswerResponse] = []

    class Config:
        from_attributes = True

class PharmacistBase(BaseModel):
    pharmacy_id: uuid.UUID

class PharmacistCreate(PharmacistBase):
    telegram_user_id: int

class PharmacistResponse(BaseModel):
    uuid: uuid.UUID
    user: UserResponse
    pharmacy: PharmacyRead
    is_active: bool

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    pharmacist: PharmacistResponse
