"""
Роутер для безопасной загрузки и обработки фото рецептов через Web Application.
Все данные хранятся исключительно на серверах РБ.

Архитектура:
- Telegram Bot: только текстовые консультации
- Web App (spravka.novamedika.com): загрузка рецептов, история консультаций
- Прямая авторизация через JWT (email/phone + пароль)
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from auth.auth import get_current_user_jwt
from db.qa_models import User
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


class PrescriptionUploadResponse(BaseModel):
    """Response model for prescription upload"""
    success: bool
    message: str
    prescription_id: str
    status: str


class PrescriptionStatusResponse(BaseModel):
    """Response model for prescription status"""
    prescription_id: str
    status: str
    created_at: str
    uploaded_at: Optional[str] = None
    answered_at: Optional[str] = None
    pharmacist_response: Optional[str] = None


@router.post("/upload", response_model=PrescriptionUploadResponse)
async def upload_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Загрузка фото рецепта напрямую через Web App.
    
    Требования:
    - JWT аутентификация (авторизация в Web App)
    - Согласие на обработку специальных ПД (consent_special_data)
    - Файл: JPEG/PNG, макс 10 MB
    
    Архитектура:
    - Пользователь авторизуется в Web App (email/phone + пароль)
    - Получает JWT токен
    - Загружает рецепт напрямую на сервер РБ
    - НЕ через Telegram!
    """
    from services.prescription_service import PrescriptionService
    from db.prescription_models import Prescription
    
    # Проверка согласия на специальные ПД
    if not hasattr(current_user, 'consent_special_data') or not current_user.consent_special_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется согласие на обработку специальных персональных данных (сведений о здоровье)"
        )
    
    # Валидация файла
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только изображения (JPEG, PNG)"
        )
    
    # Чтение файла для проверки размера
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой. Максимальный размер: 10 MB"
        )
    
    # Создание записи в БД
    prescription_uuid = uuid.uuid4()
    prescription = Prescription(
        uuid=prescription_uuid,
        user_id=current_user.uuid,
        status="pending_upload",
        file_name=file.filename,
        file_size=file_size,
        mime_type=file.content_type,
        created_at=get_utc_now_naive(),
        auto_delete_scheduled=True,
    )
    
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    
    # Сохранение файла
    try:
        service = PrescriptionService(db)
        file_path = await service.save_prescription_file(
            prescription_id=str(prescription_uuid),
            file_content=file_content,
            filename=file.filename,
        )
        
        # Обновление статуса
        prescription.status = "uploaded"
        prescription.file_path = file_path
        prescription.uploaded_at = get_utc_now_naive()
        await db.commit()
        
        logger.info(f"Prescription uploaded by user {current_user.uuid}: {prescription_uuid}")
        
        return PrescriptionUploadResponse(
            success=True,
            message="Рецепт успешно загружен. Фармацевт ответит в ближайшее время.",
            prescription_id=str(prescription_uuid),
            status="uploaded",
        )
        
    except Exception as e:
        logger.error(f"Error saving prescription file: {e}")
        # Откат транзакции
        prescription.status = "failed"
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при сохранении файла. Попробуйте позже."
        )


@router.get("/my", response_model=list[dict])
async def get_my_prescriptions(
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех моих рецептов.
    Используется в Web App для отображения истории.
    """
    from db.prescription_models import Prescription
    
    result = await db.execute(
        select(Prescription)
        .where(Prescription.user_id == current_user.uuid)
        .order_by(Prescription.created_at.desc())
    )
    prescriptions = result.scalars().all()
    
    return [
        {
            "id": str(p.uuid),
            "status": p.status,
            "file_name": p.file_name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None,
            "answered_at": p.answered_at.isoformat() if p.answered_at else None,
            "pharmacist_response": p.pharmacist_response,
        }
        for p in prescriptions
    ]


@router.get("/{prescription_id}", response_model=dict)
async def get_prescription_details(
    prescription_id: str,
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить детали конкретного рецепта с ответом фармацевта.
    """
    from db.prescription_models import Prescription
    
    result = await db.execute(
        select(Prescription).where(Prescription.uuid == prescription_id)
    )
    prescription = result.scalar_one_or_none()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рецепт не найден"
        )
    
    # Проверка доступа (только владелец или фармацевт)
    if prescription.user_id != current_user.uuid:
        # TODO: Добавить проверку роли фармацевта
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому рецепту"
        )
    
    return {
        "id": str(prescription.uuid),
        "status": prescription.status,
        "file_name": prescription.file_name,
        "file_size": prescription.file_size,
        "mime_type": prescription.mime_type,
        "created_at": prescription.created_at.isoformat() if prescription.created_at else None,
        "uploaded_at": prescription.uploaded_at.isoformat() if prescription.uploaded_at else None,
        "answered_at": prescription.answered_at.isoformat() if prescription.answered_at else None,
        "pharmacist_response": prescription.pharmacist_response,
        "auto_delete_at": prescription.auto_delete_at.isoformat() if prescription.auto_delete_at else None,
    }