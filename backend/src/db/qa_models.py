import uuid
from sqlalchemy import Column, String, Text, Boolean, BigInteger, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.database import Base
from utils.time_utils import get_utc_now_naive

class User(Base):
    __tablename__ = "qa_users"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    telegram_username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    user_type = Column(String(20), default="customer")  # customer, pharmacist
    created_at = Column(DateTime, default=get_utc_now_naive)

    questions = relationship("Question", back_populates="user")

class Pharmacist(Base):
    __tablename__ = "qa_pharmacists"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("qa_users.uuid"), nullable=False)

    # Вместо ForeignKey к Pharmacy - храним данные в JSON
    pharmacy_info = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now_naive)

    user = relationship("User")
    assigned_questions = relationship("Question", foreign_keys="Question.assigned_to", back_populates="assigned_pharmacist")
    answers = relationship("Answer", back_populates="pharmacist")

class Question(Base):
    __tablename__ = "qa_questions"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("qa_users.uuid"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, answered, closed
    category = Column(String(50), default="general")

    assigned_to = Column(UUID(as_uuid=True), ForeignKey("qa_pharmacists.uuid"), nullable=True)
    answered_by = Column(UUID(as_uuid=True), ForeignKey("qa_pharmacists.uuid"), nullable=True)

    context_data = Column(JSON, nullable=True)  
    created_at = Column(DateTime, default=get_utc_now_naive)
    answered_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="questions")
    assigned_pharmacist = relationship("Pharmacist", foreign_keys=[assigned_to], back_populates="assigned_questions")
    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "qa_answers"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("qa_questions.uuid"), nullable=False)
    pharmacist_id = Column(UUID(as_uuid=True), ForeignKey("qa_pharmacists.uuid"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now_naive)

    question = relationship("Question", back_populates="answers")
    pharmacist = relationship("Pharmacist", back_populates="answers")
