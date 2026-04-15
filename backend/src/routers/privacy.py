# Privacy router — реализация прав субъектов персональных данных
# Требование ОАЦ №66 + Закон №99-З «О защите персональных данных»
#
# Эндпоинты:
#   GET    /api/privacy/my-data         — получить копию своих ПД
#   PUT    /api/privacy/profile         — изменить свои ПД
#   DELETE /api/privacy/delete-account  — удалить аккаунт и ПД
#   GET    /api/privacy/export-data     — экспорт всех данных в JSON

import uuid
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from db.database import get_db
from auth.security import get_current_user
from db.qa_models import User, Pharmacist, Question, Answer, DialogMessage
from db.booking_models import BookingOrder

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


# === Pydantic схемы ===

class ProfileUpdate(BaseModel):
    """Данные для обновления профиля"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    telegram_username: Optional[str] = Field(None, max_length=100)


class DeleteAccountRequest(BaseModel):
    """Запрос на удаление аккаунта"""
    confirm: bool = Field(..., description="Подтверждение удаления (должно быть true)")
    reason: Optional[str] = Field(None, max_length=500)


class MyDataResponse(BaseModel):
    """Ответ с данными пользователя"""
    user: dict
    pharmacist: Optional[dict] = None
    questions: list[dict] = []
    orders: list[dict] = []
    exported_at: str


class DeleteAccountResponse(BaseModel):
    """Ответ после удаления аккаунта"""
    success: bool
    message: str
    deleted_at: str


class ExportDataResponse(BaseModel):
    """Экспорт данных в машиночитаемом формате"""
    user_id: str
    export_format: str = "json"
    data: dict
    exported_at: str


# === Вспомогательные функции ===

def _serialize(obj) -> dict:
    """Сериализует SQLAlchemy модель в dict"""
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, uuid.UUID):
            value = str(value)
        result[column.name] = value
    return result


def _anonymize_user(user: User):
    """Анонимизирует персональные данные пользователя"""
    user.first_name = "Анонимизирован"
    user.last_name = ""
    user.phone = ""
    user.telegram_username = ""
    # telegram_id и uuid сохраняем для целостности БД


# === Эндпоинты ===

@router.get("/my-data", response_model=MyDataResponse)
async def get_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Право на доступ к персональным данным (ст. 14 Закона №99-З).
    Возвращает копию всех ПД пользователя.
    """
    # Данные пользователя
    user_data = _serialize(current_user)

    # Данные фармацевта (если есть)
    pharmacist_data = None
    pharmacist_result = await db.execute(
        select(Pharmacist).where(Pharmacist.user_id == current_user.uuid)
    )
    pharmacist = pharmacist_result.scalar_one_or_none()
    if pharmacist:
        pharmacist_data = _serialize(pharmacist)
        # Убираем чувствительные поля из pharmacy_info
        if pharmacist_data.get("pharmacy_info"):
            pharmacist_data["pharmacy_info"] = {
                k: v for k, v in pharmacist.pharmacy_info.items()
                if k != "auth_token"
            }

    # Вопросы пользователя
    questions_result = await db.execute(
        select(Question)
        .where(Question.user_id == current_user.uuid)
        .options(selectinload(Question.dialog_messages))
        .order_by(Question.created_at.desc())
    )
    questions = questions_result.scalars().all()
    questions_data = []
    for q in questions:
        q_data = _serialize(q)
        q_data["dialog_messages"] = [_serialize(m) for m in q.dialog_messages]
        questions_data.append(q_data)

    # Заказы пользователя (по telegram_id)
    orders_result = await db.execute(
        select(BookingOrder)
        .where(BookingOrder.telegram_id == current_user.telegram_id)
        .order_by(BookingOrder.created_at.desc())
    )
    orders = orders_result.scalars().all()
    orders_data = [_serialize(o) for o in orders]

    return MyDataResponse(
        user=user_data,
        pharmacist=pharmacist_data,
        questions=questions_data,
        orders=orders_data,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )


@router.put("/profile", response_model=dict)
async def update_profile(
    profile: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Право на изменение персональных данных (ст. 14 Закона №99-З).
    Позволяет обновить ФИ, телефон, username.
    """
    updated_fields = []

    if profile.first_name is not None:
        current_user.first_name = profile.first_name
        updated_fields.append("first_name")

    if profile.last_name is not None:
        current_user.last_name = profile.last_name
        updated_fields.append("last_name")

    if profile.phone is not None:
        current_user.phone = profile.phone
        updated_fields.append("phone")

    if profile.telegram_username is not None:
        current_user.telegram_username = profile.telegram_username
        updated_fields.append("telegram_username")

    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    await db.commit()

    return {
        "success": True,
        "message": f"Updated fields: {', '.join(updated_fields)}",
        "updated_fields": updated_fields,
    }


@router.delete("/delete-account", response_model=DeleteAccountResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Право на удаление персональных данных (ст. 14 Закона №99-З).
    Анонимизирует ПД пользователя (soft delete для целостности БД).
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation is required (confirm=true)",
        )

    user_uuid = current_user.uuid
    telegram_id = current_user.telegram_id

    # 1. Анонимизируем пользователя
    _anonymize_user(current_user)
    await db.commit()

    # 2. Анонимизируем вопросы (тексты вопросов могут содержать ПД)
    questions_result = await db.execute(
        select(Question).where(Question.user_id == user_uuid)
    )
    questions = questions_result.scalars().all()
    for q in questions:
        q.text = "[Анонимизировано]"
        if q.context_data:
            q.context_data = {}
    await db.commit()

    # 3. Анонимизируем заказы (если есть)
    if telegram_id:
        orders_result = await db.execute(
            select(BookingOrder).where(BookingOrder.telegram_id == telegram_id)
        )
        orders = orders_result.scalars().all()
        for order in orders:
            order.customer_name = "Анонимизирован"
            order.customer_phone = ""
        await db.commit()

    # 4. Если фармацевт — деактивируем
    pharmacist_result = await db.execute(
        select(Pharmacist).where(Pharmacist.user_id == user_uuid)
    )
    pharmacist = pharmacist_result.scalar_one_or_none()
    if pharmacist:
        pharmacist.is_active = False
        pharmacist.pharmacy_info = {}
        await db.commit()

    return DeleteAccountResponse(
        success=True,
        message="Account anonymized. Personal data has been removed.",
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/export-data", response_model=ExportDataResponse)
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Право на получение копии ПД в машиночитаемом формате (ст. 14 Закона №99-З).
    Возвращает все данные пользователя в JSON формате.
    """
    # Собираем все данные
    export = {
        "user": _serialize(current_user),
        "pharmacist": None,
        "questions": [],
        "answers": [],
        "orders": [],
    }

    # Фармацевт
    pharmacist_result = await db.execute(
        select(Pharmacist).where(Pharmacist.user_id == current_user.uuid)
    )
    pharmacist = pharmacist_result.scalar_one_or_none()
    if pharmacist:
        export["pharmacist"] = _serialize(pharmacist)
        if export["pharmacist"].get("pharmacy_info"):
            export["pharmacist"]["pharmacy_info"] = {
                k: v for k, v in pharmacist.pharmacy_info.items()
                if k != "auth_token"
            }

    # Вопросы + ответы + диалоги
    questions_result = await db.execute(
        select(Question)
        .where(Question.user_id == current_user.uuid)
        .options(
            selectinload(Question.dialog_messages),
            selectinload(Question.answers),
        )
        .order_by(Question.created_at.desc())
    )
    questions = questions_result.scalars().all()
    for q in questions:
        export["questions"].append({
            "uuid": str(q.uuid),
            "text": q.text,
            "status": q.status,
            "category": q.category,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "answered_at": q.answered_at.isoformat() if q.answered_at else None,
            "dialog_messages": [
                {
                    "uuid": str(m.uuid),
                    "message_type": m.message_type,
                    "sender_type": m.sender_type,
                    "text": m.text,
                    "file_id": m.file_id,
                    "caption": m.caption,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in q.dialog_messages
            ],
        })
        for a in q.answers:
            export["answers"].append({
                "uuid": str(a.uuid),
                "question_id": str(a.question_id),
                "text": a.text,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    # Заказы
    if current_user.telegram_id:
        orders_result = await db.execute(
            select(BookingOrder)
            .where(BookingOrder.telegram_id == current_user.telegram_id)
            .order_by(BookingOrder.created_at.desc())
        )
        orders = orders_result.scalars().all()
        export["orders"] = [_serialize(o) for o in orders]

    return ExportDataResponse(
        user_id=str(current_user.uuid),
        export_format="json",
        data=export,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )
