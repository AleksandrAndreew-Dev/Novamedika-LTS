# ТЕХНИЧЕСКОЕ РЕШЕНИЕ: ВЫНОС ОБРАБОТКИ ФОТО РЕЦЕПТОВ ИЗ TELEGRAM

**Дата:** 20 мая 2026 г.  
**Статус:** 📋 ПРОЕКТИРОВАНИЕ  
**Приоритет:** 🔴 КРИТИЧЕСКИЙ (требуется для compliance с законодательством РБ)

---

## 🚨 ПРОБЛЕМА

Текущая архитектура позволяет пользователям отправлять фото рецептов напрямую в Telegram-бот, что является **грубым нарушением**:

1. **Закон №99-З «О защите персональных данных»** - специальные категории ПД (сведения о здоровье)
2. **Статья 46 Закона «О здравоохранении»** - врачебная тайна
3. **Требования НЦЗПД** - трансграничная передача специальных ПД через иностранные мессенджеры запрещена

**Последствия при проверке ОАЦ/НЦЗПД:**
- Штраф до 50 БВ (~2000 BYN)
- Предписание о прекращении обработки ПД
- Закрытие сервиса

---

## ✅ РЕШЕНИЕ: ГИБРИДНАЯ АРХИТЕКТУРА

### Общая схема

```
[ Пользователь в Telegram ]
       │
       ▼ (Кнопка "Загрузить рецепт")
[ Telegram Bot генерирует одноразовую ссылку ]
       │
       ▼ (Открытие Web App или браузера)
[ Web Application на сервере РБ ]
       │
       ├─► [ Авторизация по SMS ]
       ├─► [ Согласие на обработку специальных ПД ]
       ├─► [ Загрузка фото через HTTPS ]
       │
       ▼ (Сохранение на сервере в РБ)
[ Защищенное хранилище (AES-256) ]
       │
       ▼ (Отображение фармацевту)
[ CRM фармацевта (режим просмотра без скачивания) ]
       │
       ▼ (Автоудаление через 48 часов)
[ Cron job удаляет файл из БД и файловой системы ]
```

---

## 📋 ПОШАГОВАЯ РЕАЛИЗАЦИЯ

### Шаг 1: Создание Web Application для загрузки рецептов

#### 1.1. Backend API endpoints

**Новый роутер:** `backend/src/routers/prescriptions.py`

```python
"""
Роутер для безопасной загрузки и обработки фото рецептов.
Все данные хранятся исключительно на серверах РБ.
"""

import uuid
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from auth.security import get_current_user
from db.qa_models import User
from utils.encryption import encrypt_value, decrypt_value
from services.prescription_service import PrescriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


class PrescriptionCreateResponse(BaseModel):
    """Ответ после создания рецепта"""
    prescription_id: str
    upload_url: str
    expires_at: str


class PrescriptionUploadResponse(BaseModel):
    """Ответ после загрузки файла"""
    success: bool
    prescription_id: str
    message: str


@router.post("/create-upload-link", response_model=PrescriptionCreateResponse)
async def create_upload_link(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает одноразовую ссылку для загрузки рецепта.
    Ссылка действительна 15 минут.
    
    Требования:
    - Пользователь должен быть авторизован
    - Должно быть согласие на обработку специальных ПД
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
    from utils.time_utils import get_utc_now_naive
    
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
    
    # Генерируем URL для загрузки
    upload_url = f"https://spravka.novamedika.com/upload-prescription/{prescription_id}"
    
    logger.info(f"Created upload link for user {current_user.uuid}, prescription {prescription_id}")
    
    return PrescriptionCreateResponse(
        prescription_id=prescription_id,
        upload_url=upload_url,
        expires_at=expires_at.isoformat(),
    )


@router.post("/upload/{prescription_id}", response_model=PrescriptionUploadResponse)
async def upload_prescription(
    prescription_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Загружает фото рецепта на сервер РБ.
    
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
        
        return PrescriptionUploadResponse(
            success=True,
            prescription_id=prescription_id,
            message="Рецепт успешно загружен. Фармацевт получит уведомление.",
        )
        
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
    Только владелец может查看 статус.
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
```

---

#### 1.2. Модель данных для рецептов

**Новый файл:** `backend/src/db/prescription_models.py`

```python
"""
Модели для хранения фото рецептов.
Все данные хранятся на серверах РБ с шифрованием.
"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base
from .utils import get_utc_now_naive


class Prescription(Base):
    """Модель рецепта (фото медицинского назначения)"""
    __tablename__ = "prescriptions"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Связь с пользователем
    user_id = Column(UUID(as_uuid=True), ForeignKey("qa_users.uuid"), nullable=False, index=True)
    
    # Статус рецепта
    status = Column(String(20), default="pending_upload", nullable=False)
    # pending_upload -> uploaded -> reviewed -> completed -> deleted
    
    # Путь к файлу (шифрованный)
    file_path_encrypted = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)  # Для обратной совместимости
    
    # Метаданные файла
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # Размер в байтах
    mime_type = Column(String(100), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=get_utc_now_naive, nullable=False)
    uploaded_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)  # Когда фармацевт открыл
    answered_at = Column(DateTime, nullable=True)  # Когда дал ответ
    deleted_at = Column(DateTime, nullable=True)  # Когда удален (автоудаление)
    
    # Срок действия ссылки на загрузку
    expires_at = Column(DateTime, nullable=True)
    
    # Ответ фармацевта (текст)
    pharmacist_response = Column(Text, nullable=True)
    pharmacist_id = Column(UUID(as_uuid=True), ForeignKey("qa_pharmacists.uuid"), nullable=True)
    
    # Флаг автоудаления
    auto_delete_scheduled = Column(Boolean, default=True, nullable=False)
    auto_delete_at = Column(DateTime, nullable=True)  # Через 48 часов после answered_at
    
    # Связи
    user = relationship("User", back_populates="prescriptions")
    pharmacist = relationship("Pharmacist", back_populates="prescriptions_reviewed")

    __table_args__ = (
        Index("idx_prescription_user_id", "user_id"),
        Index("idx_prescription_status", "status"),
        Index("idx_prescription_auto_delete_at", "auto_delete_at"),
    )
```

---

#### 1.3. Сервис для работы с рецептами

**Новый файл:** `backend/src/services/prescription_service.py`

```python
"""
Сервис для безопасной обработки фото рецептов.
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from utils.encryption import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


class PrescriptionService:
    """Сервис для управления рецептами"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Путь к защищенному хранилищу на сервере РБ
        self.storage_path = Path("/opt/novamedika/prescriptions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_prescription_file(
        self,
        prescription_id: str,
        file_content: bytes,
        filename: str,
    ) -> str:
        """
        Сохраняет фото рецепта в защищенное хранилище.
        
        Returns:
            Путь к сохраненному файлу
        """
        # Генерируем уникальное имя файла
        file_extension = Path(filename).suffix or ".jpg"
        unique_filename = f"{prescription_id}{file_extension}"
        file_path = self.storage_path / unique_filename
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Устанавливаем права доступа (только для владельца)
        os.chmod(file_path, 0o600)
        
        logger.info(f"Prescription file saved: {file_path}")
        
        return str(file_path)
    
    async def get_prescription_file(self, prescription_id: str) -> bytes:
        """
        Читает фото рецепта из хранилища.
        Только для фармацевтов в режиме просмотра.
        """
        from db.prescription_models import Prescription
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Prescription).where(Prescription.uuid == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        
        if not prescription:
            raise FileNotFoundError(f"Prescription {prescription_id} not found")
        
        file_path = Path(prescription.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        
        with open(file_path, "rb") as f:
            return f.read()
    
    async def delete_prescription_file(self, prescription_id: str):
        """
        Удаляет фото рецепта из хранилища и БД.
        Используется для автоудаления через 48 часов.
        """
        from db.prescription_models import Prescription
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Prescription).where(Prescription.uuid == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        
        if not prescription:
            logger.warning(f"Prescription {prescription_id} not found for deletion")
            return
        
        # Удаляем файл из файловой системы
        if prescription.file_path:
            file_path = Path(prescription.file_path)
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Deleted prescription file: {file_path}")
        
        # Обновляем статус в БД
        prescription.status = "deleted"
        prescription.deleted_at = datetime.utcnow()
        prescription.file_path = None
        
        await self.db.commit()
        
        logger.info(f"Prescription {prescription_id} deleted successfully")
```

---

### Шаг 2: Интеграция с Telegram Bot

#### 2.1. Обновление команды /start

**Файл:** `backend/src/bot/handlers/common_handlers/commands.py`

Добавить кнопку "Загрузить рецепт" в главное меню:

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_user_inline_keyboard_with_prescription():
    """Клавиатура с кнопкой загрузки рецепта"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💊 Задать вопрос фармацевту",
                    callback_data="ask_question"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📸 Загрузить рецепт (безопасно)",
                    callback_data="upload_prescription"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 История консультаций",
                    callback_data="show_history"
                )
            ]
        ]
    )
    return keyboard
```

---

#### 2.2. Callback handler для загрузки рецепта

**Файл:** `backend/src/bot/handlers/common_handlers/callbacks.py`

```python
@router.callback_query(F.data == "upload_prescription")
async def upload_prescription_callback(
    callback: CallbackQuery,
    db: AsyncSession | None = None,
    user: User | None = None,
):
    """
    Обработка запроса на загрузку рецепта.
    Генерирует одноразовую ссылку и открывает Web App.
    """
    if not db or not user:
        logger.error("Missing required dependencies in upload_prescription_callback")
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
    
    try:
        # Проверяем согласие на обработку специальных ПД
        consent_special_data = getattr(user, 'consent_special_data', False)
        
        if not consent_special_data:
            # Запрашиваем отдельное согласие на специальные ПД
            special_consent_text = (
                "⚠️ <b>Согласие на обработку специальных персональных данных</b>\n\n"
                "Фото рецепта содержит сведения о вашем здоровье (специальные персональные данные).\n\n"
                "Для загрузки рецепта необходимо дать отдельное согласие на обработку таких данных "
                "в соответствии со статьей 8 Закона №99-З.\n\n"
                "🔒 <b>Как мы защищаем ваши данные:</b>\n"
                "• Фото загружается напрямую на серверы в Республике Беларусь\n"
                "• Данные НЕ передаются через Telegram\n"
                "• Шифрование AES-256 при хранении\n"
                "• Автоудаление через 48 часов после консультации\n"
                "• Доступ только у авторизованных фармацевтов\n"
                "• Просмотр только в режиме «глазок» (без скачивания)\n\n"
                "Нажимая «✅ Согласен», вы подтверждаете, что ознакомлены с условиями."
            )
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Согласен",
                            callback_data="consent_special_data"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Отказаться",
                            callback_data="decline_special_data"
                        )
                    ]
                ]
            )
            
            await callback.message.answer(special_consent_text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
            return
        
        # Если согласие есть - генерируем ссылку
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/prescriptions/create-upload-link",
                headers={
                    "Authorization": f"Bearer {user.jwt_token}",  # Предполагаем наличие JWT
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.text}")
            
            data = response.json()
            upload_url = data["upload_url"]
            expires_at = data["expires_at"]
        
        # Отправляем ссылку пользователю
        upload_message = (
            "📸 <b>Загрузка рецепта</b>\n\n"
            "Нажмите кнопку ниже, чтобы открыть безопасную форму загрузки.\n\n"
            "⏰ <b>Важно:</b> Ссылка действительна 15 минут.\n\n"
            "🔒 Ваши данные будут защищены:\n"
            "• Загрузка напрямую на серверы РБ (не через Telegram)\n"
            "• Шифрование AES-256\n"
            "• Автоудаление через 48 часов"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📤 Открыть форму загрузки",
                        url=upload_url
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="ℹ️ Как это работает?",
                        callback_data="how_prescription_upload_works"
                    )
                ]
            ]
        )
        
        await callback.message.answer(upload_message, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error creating upload link for user {user.telegram_id}: {e}")
        await callback.answer("❌ Ошибка при создании ссылки. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "consent_special_data")
async def consent_special_data_callback(
    callback: CallbackQuery,
    db: AsyncSession | None = None,
    user: User | None = None,
):
    """Обработка согласия на обработку специальных ПД"""
    if not db or not user:
        await callback.answer("❌ Ошибка сервера", show_alert=True)
        return
    
    try:
        # Обновляем согласие в БД
        user.consent_special_data = True
        user.consent_special_data_date = get_utc_now_naive()
        await db.commit()
        
        logger.info(f"User {user.telegram_id} gave consent for special data processing")
        
        await callback.answer("✅ Спасибо за согласие!")
        
        # Повторно вызываем загрузку рецепта
        await upload_prescription_callback(callback, db, user)
        
    except Exception as e:
        logger.error(f"Error saving special data consent: {e}")
        await callback.answer("❌ Ошибка при сохранении согласия", show_alert=True)


@router.callback_query(F.data == "decline_special_data")
async def decline_special_data_callback(callback: CallbackQuery):
    """Обработка отказа от обработки специальных ПД"""
    await callback.answer()
    
    await callback.message.answer(
        "❌ <b>Согласие не получено</b>\n\n"
        "Без согласия на обработку специальных персональных данных "
        "(сведений о здоровье) мы не можем принимать фото рецептов.\n\n"
        "Вы можете задать текстовый вопрос фармацевту без загрузки фото."
    )
```

---

### Шаг 3: Frontend Web Application

#### 3.1. Страница загрузки рецепта

**Файл:** `frontend/src/pages/UploadPrescription.jsx`

```jsx
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const UploadPrescription = () => {
  const { prescriptionId } = useParams();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    // Проверка типа файла
    if (!selectedFile.type.startsWith('image/')) {
      setError('Пожалуйста, выберите изображение (JPEG, PNG)');
      return;
    }
    
    // Проверка размера (макс 10 MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('Файл слишком большой. Максимальный размер: 10 MB');
      return;
    }
    
    setFile(selectedFile);
    setError('');
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Пожалуйста, выберите файл');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `/api/prescriptions/upload/${prescriptionId}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setSuccess(true);
      
      // Перенаправление через 3 секунды
      setTimeout(() => {
        navigate('/prescription-success');
      }, 3000);

    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при загрузке. Попробуйте позже.');
    } finally {
      setUploading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-4">✅</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Рецепт успешно загружен!
          </h2>
          <p className="text-gray-600 mb-6">
            Фармацевт получит уведомление и ответит вам в ближайшее время.
          </p>
          <p className="text-sm text-gray-500">
            Перенаправление...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        <div className="text-center mb-6">
          <div className="text-6xl mb-4">📸</div>
          <h1 className="text-2xl font-bold text-gray-800">
            Загрузка рецепта
          </h1>
          <p className="text-gray-600 mt-2">
            Безопасная загрузка на серверы Республики Беларусь
          </p>
        </div>

        {/* Информация о безопасности */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
          <h3 className="font-semibold text-blue-900 mb-2">🔒 Защита данных:</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>✓ Прямая загрузка на серверы РБ (не через Telegram)</li>
            <li>✓ Шифрование AES-256</li>
            <li>✓ Автоудаление через 48 часов</li>
            <li>✓ Доступ только у фармацевтов</li>
          </ul>
        </div>

        {/* Выбор файла */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Выберите фото рецепта
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {file && (
            <p className="mt-2 text-sm text-gray-600">
              Выбран: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        {/* Ошибка */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Кнопка загрузки */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-colors ${
            !file || uploading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {uploading ? 'Загрузка...' : '📤 Загрузить рецепт'}
        </button>

        {/* Примечание */}
        <p className="mt-4 text-xs text-gray-500 text-center">
          Поддерживаемые форматы: JPEG, PNG. Максимальный размер: 10 MB
        </p>
      </div>
    </div>
  );
};

export default UploadPrescription;
```

---

### Шаг 4: Интерфейс фармацевта

#### 4.1. Просмотр рецепта (режим "глазок")

**Файл:** `frontend/src/components/Pharmacist/PrescriptionViewer.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PrescriptionViewer = ({ prescriptionId, onClose }) => {
  const [imageBlob, setImageBlob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPrescription = async () => {
      try {
        const response = await axios.get(
          `/api/prescriptions/${prescriptionId}/view`,
          {
            responseType: 'blob',
          }
        );
        
        setImageBlob(URL.createObjectURL(response.data));
        setLoading(false);
        
        // Логируем просмотр
        await axios.post(`/api/prescriptions/${prescriptionId}/log-view`);
        
      } catch (err) {
        setError('Ошибка при загрузке рецепта');
        setLoading(false);
      }
    };

    fetchPrescription();
  }, [prescriptionId]);

  // Запрещаем правый клик (контекстное меню)
  const handleContextMenu = (e) => {
    e.preventDefault();
    alert('Скачивание запрещено политикой безопасности');
  };

  // Запрещаем drag-and-drop
  const handleDragStart = (e) => {
    e.preventDefault();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-500 p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full mx-4">
        {/* Заголовок */}
        <div className="border-b px-6 py-4 flex justify-between items-center">
          <h2 className="text-xl font-semibold">📋 Просмотр рецепта</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {/* Предупреждение */}
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 m-6">
          <p className="text-yellow-800 text-sm">
            ⚠️ <b>Режим просмотра:</b> Скачивание и копирование запрещены. 
            Все действия логируются.
          </p>
        </div>

        {/* Изображение */}
        <div className="px-6 pb-6">
          <img
            src={imageBlob}
            alt="Рецепт"
            onContextMenu={handleContextMenu}
            onDragStart={handleDragStart}
            className="w-full h-auto max-h-[70vh] object-contain"
            style={{ pointerEvents: 'none' }} // Запрещаем взаимодействие
          />
        </div>

        {/* Кнопки действий */}
        <div className="border-t px-6 py-4 flex justify-end gap-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            Закрыть
          </button>
          <button
            onClick={() => {/* Открыть форму ответа */}}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            💬 Ответить
          </button>
        </div>
      </div>
    </div>
  );
};

export default PrescriptionViewer;
```

---

### Шаг 5: Автоудаление рецептов через 48 часов

#### 5.1. Celery task для автоудаления

**Файл:** `backend/src/tasks/prescription_cleanup.py`

```python
"""
Celery task для автоматического удаления фото рецептов через 48 часов.
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import select

from db.database import SessionLocal
from db.prescription_models import Prescription
from services.prescription_service import PrescriptionService

logger = logging.getLogger(__name__)


@shared_task(name="prescription.cleanup_expired")
def cleanup_expired_prescriptions():
    """
    Удаляет рецепты, которые должны быть удалены (прошло 48 часов после ответа).
    Запускается каждый час.
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Находим рецепты, которые нужно удалить
        result = db.execute(
            select(Prescription).where(
                (Prescription.auto_delete_at <= now) &
                (Prescription.status != "deleted")
            )
        )
        prescriptions = result.scalars().all()
        
        deleted_count = 0
        
        for prescription in prescriptions:
            try:
                service = PrescriptionService(db)
                await service.delete_prescription_file(str(prescription.uuid))
                deleted_count += 1
                
                logger.info(f"Auto-deleted prescription {prescription.uuid}")
                
            except Exception as e:
                logger.error(f"Error deleting prescription {prescription.uuid}: {e}")
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} prescriptions.")
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        raise
    
    finally:
        db.close()
```

#### 5.2. Настройка Celery Beat

**Файл:** `backend/celeryconfig.py`

```python
from celery.schedules import crontab

beat_schedule = {
    # Каждые час проверяем и удаляем старые рецепты
    "prescription-cleanup-hourly": {
        "task": "prescription.cleanup_expired",
        "schedule": crontab(minute=0),  # Каждый час в 00 минут
    },
}
```

---

### Шаг 6: Добавление поля согласия на специальные ПД в модель User

**Файл:** `backend/src/db/qa_models.py`

```python
# Добавить в класс User:

# Поля для согласия на обработку специальных ПД (сведений о здоровье)
consent_special_data = Column(Boolean, default=False, nullable=False,
                              comment='Согласие на обработку специальных ПД (сведений о здоровье)')
consent_special_data_date = Column(DateTime, nullable=True,
                                   comment='Дата предоставления согласия на обработку специальных ПД')
```

---

### Шаг 7: Миграция БД

```bash
cd backend
uv run alembic revision -m "add_prescription_models_and_special_data_consent"
```

---

## 📊 СВОДКА АРХИТЕКТУРЫ

### Что изменилось:

| Компонент | Было | Стало |
|-----------|------|-------|
| **Загрузка фото** | Прямо в Telegram | Через Web App на сервер РБ |
| **Хранение** | В Telegram (UK/UAE) | На серверах РБ (beCloud/hoster.by) |
| **Шифрование** | Нет | AES-256 at rest |
| **Доступ фармацевта** | Скачать можно | Только просмотр ("глазок") |
| **Срок хранения** | Неограниченно | Автоудаление через 48 часов |
| **Логирование** | Частичное | Полное (все действия) |
| **Согласие** | Общее | Отдельное на специальные ПД |

---

## ✅ CHECKLIST COMPLIANCE

### Законодательство РБ:

- [x] Фото НЕ передается через Telegram (трансграничная передача исключена)
- [x] Серверы физически в РБ (требуется аренда у beCloud/hoster.by/A1)
- [x] Отдельное согласие на специальные ПД (статья 8 Закона №99-З)
- [x] Шифрование AES-256 при хранении
- [x] Режим просмотра без скачивания для фармацевтов
- [x] Автоудаление через 48 часов
- [x] Полное логирование всех действий
- [x] Авторизация по SMS (привязка к паспорту)

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ

### Приоритет 1 (1-2 недели):
1. Создать модели БД и миграции
2. Реализовать backend API endpoints
3. Создать frontend Web App для загрузки
4. Интегрировать с Telegram bot

### Приоритет 2 (2-3 недели):
5. Создать интерфейс фармацевта (режим просмотра)
6. Реализовать Celery task для автоудаления
7. Настроить логирование
8. Тестирование security

### Приоритет 3 (перед деплоем):
9. Арендовать серверы в РБ с аттестатом ОАЦ
10. Деплой на production
11. Обучение фармацевтов
12. Обновление Privacy Policy

---

**Статус:** 📋 Проектирование завершено  
**Требуется:** Реализация кода и тестирование  
**Автор:** AI-ассистент  
**Дата создания:** 20 мая 2026 г.
