"""
Роутер для безопасной загрузки и обработки фото рецептов через Telegram Web App.
Все данные хранятся исключительно на серверах РБ.
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
from auth.security import get_current_user
from db.qa_models import User
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


class PrescriptionCreateResponse(BaseModel):
    """Ответ после создания ссылки на загрузку рецепта"""
    prescription_id: str
    upload_url: str
    expires_at: str


class PrescriptionUploadResponse(BaseModel):
    """Ответ после загрузки файла"""
    success: bool
    prescription_id: str
    message: str


@router.post("/create-upload-link")
async def create_upload_link(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает одноразовую ссылку для загрузки рецепта через Telegram Web App.
    Ссылка действительна 15 минут.
    
    Требования:
    - Пользователь должен быть авторизован
    - Должно быть согласие на обработку специальных ПД (consent_special_data)
    """
    # Проверяем согласие на обработку специальных ПД
    if not hasattr(current_user, 'consent_special_data') or not current_user.consent_special_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется согласие на обработку специальных персональных данных (сведений о здоровье)"
        )
    
    # Генерируем уникальный ID рецепта
    prescription_id = str(uuid.uuid4())
    
    # Создаем запись в БД со статусом "ожидает загрузки"
    from db.prescription_models import Prescription
    
    expires_at = get_utc_now_naive() + timedelta(minutes=15)
    
    prescription = Prescription(
        uuid=prescription_id,
        user_id=current_user.uuid,
        status="pending_upload",
        expires_at=expires_at,
        created_at=get_utc_now_naive(),
    )
    
    db.add(prescription)
    await db.commit()
    
    # Генерируем URL для загрузки (Telegram Web App откроет эту страницу)
    upload_url = f"https://spravka.novamedika.com/upload-prescription/{prescription_id}"
    
    logger.info(f"Created upload link for user {current_user.uuid}, prescription {prescription_id}")
    
    return {
        "prescription_id": prescription_id,
        "upload_url": upload_url,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/upload/{prescription_id}")
async def upload_prescription(
    prescription_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Загружает фото рецепта на сервер РБ через Telegram Web App.
    
    Требования:
    - Файл должен быть изображением (JPEG, PNG)
    - Максимальный размер: 10 MB
    - Ссылка должна быть действительна
    """
    from db.prescription_models import Prescription
    
    # Проверяем существование рецепта
    result = await db.execute(
        select(Prescription).where(Prescription.uuid == prescription_id)
    )
    prescription = result.scalar_one_or_none()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рецепт не найден"
        )
    
    # Проверяем срок действия ссылки
    if prescription.expires_at < get_utc_now_naive():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Ссылка для загрузки истекла. Создайте новую."
        )
    
    # Проверяем тип файла
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(allowed_types)}"
        )
    
    # Проверяем размер файла (макс 10 MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл слишком большой. Максимальный размер: 10 MB"
        )
    
    # Сохраняем файл на сервере РБ
    try:
        from services.prescription_service import PrescriptionService
        
        service = PrescriptionService(db)
        file_path = await service.save_prescription_file(
            prescription_id=prescription_id,
            file_content=file_content,
            filename=file.filename,
        )
        
        # Обновляем статус рецепта
        prescription.status = "uploaded"
        prescription.file_path = file_path
        prescription.uploaded_at = get_utc_now_naive()
        
        await db.commit()
        
        logger.info(f"Prescription {prescription_id} uploaded successfully by user {prescription.user_id}")
        
        return {
            "success": True,
            "prescription_id": prescription_id,
            "message": "Рецепт успешно загружен. Фармацевт получит уведомление.",
        }
        
    except Exception as e:
        logger.error(f"Error uploading prescription {prescription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке рецепта. Попробуйте позже."
        )


@router.get("/{prescription_id}/status")
async def get_prescription_status(
    prescription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получение статуса рецепта.
    Только владелец может просмотреть статус.
    """
    from db.prescription_models import Prescription
    
    result = await db.execute(
        select(Prescription).where(
            (Prescription.uuid == prescription_id) & 
            (Prescription.user_id == current_user.uuid)
        )
    )
    prescription = result.scalar_one_or_none()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рецепт не найден"
        )
    
    return {
        "prescription_id": prescription_id,
        "status": prescription.status,
        "created_at": prescription.created_at.isoformat() if prescription.created_at else None,
        "uploaded_at": prescription.uploaded_at.isoformat() if prescription.uploaded_at else None,
        "answered_at": prescription.answered_at.isoformat() if prescription.answered_at else None,
        "expires_at": prescription.expires_at.isoformat() if prescription.expires_at else None,
    }
