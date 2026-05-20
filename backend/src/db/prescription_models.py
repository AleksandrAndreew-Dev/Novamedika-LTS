"""
Модели для хранения фото рецептов.
Все данные хранятся на серверах РБ с шифрованием.
"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Index
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
    
    # Путь к файлу (хранится в защищенном хранилище на сервере РБ)
    file_path = Column(String(500), nullable=True)
    
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
