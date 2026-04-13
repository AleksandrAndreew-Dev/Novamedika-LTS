"""Модель для хранения refresh токенов."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.base import Base
from utils.time_utils import get_utc_now_naive


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("qa_users.uuid"), nullable=False)
    token = Column(Text, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_utc_now_naive, nullable=False)

    # Связь с пользователем
    user = relationship("User", back_populates="refresh_tokens")
