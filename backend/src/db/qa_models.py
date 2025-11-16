import uuid
from sqlalchemy import (
    Column,
    String,
    Date,
    ForeignKey,
    Numeric,
    DateTime,
    UniqueConstraint,
    Boolean,
    BigInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from db.database import Base
from utils.time_utils import get_utc_now_naive

class User(Base):
    __tablename__ = "users"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    telegram_username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_utc_now_naive)
    questions = relationship("Question", back_populates="user")

class Pharmacist(Base):
    __tablename__ = "pharmacists"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    pharmacy_id = Column(
        UUID(as_uuid=True), ForeignKey("pharmacies.uuid"), nullable=False
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now_naive)

    user = relationship("User")
    pharmacy = relationship("Pharmacy")
    assigned_questions = relationship("Question", foreign_keys="Question.assigned_to", back_populates="assigned_pharmacist")
    answered_questions = relationship("Question", foreign_keys="Question.answered_by", back_populates="answered_by_rel")
    answers = relationship("Answer", back_populates="pharmacist")

class Question(Base):
    __tablename__ = "questions"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, answered, closed
    assigned_to = Column(
        UUID(as_uuid=True), ForeignKey("pharmacists.uuid"), nullable=True
    )
    answered_by = Column(
        UUID(as_uuid=True), ForeignKey("pharmacists.uuid"), nullable=True
    )
    parent_question_id = Column(
        UUID(as_uuid=True), ForeignKey("questions.uuid"), nullable=True
    )
    created_at = Column(DateTime, default=get_utc_now_naive)
    answered_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="questions")
    assigned_pharmacist = relationship("Pharmacist", foreign_keys=[assigned_to], back_populates="assigned_questions")
    answered_by_rel = relationship("Pharmacist", foreign_keys=[answered_by], back_populates="answered_questions")
    parent_question = relationship(
        "Question", remote_side=[uuid], backref="followup_questions"
    )
    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True), ForeignKey("questions.uuid"), nullable=False
    )
    pharmacist_id = Column(
        UUID(as_uuid=True), ForeignKey("pharmacists.uuid"), nullable=False
    )
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now_naive)

    question = relationship("Question", back_populates="answers")
    pharmacist = relationship("Pharmacist", back_populates="answers")
