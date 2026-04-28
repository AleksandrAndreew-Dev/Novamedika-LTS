"""Router for Pharmacist WebApp Dashboard - Consultations Management"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import logging

from db.database import get_db
from db.qa_models import Question, User, Pharmacist, DialogMessage
from auth.auth import get_current_pharmacist
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Pharmacist Dashboard"],
)


# Pydantic Schemas
class QuestionResponse(BaseModel):
    uuid: str
    text: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_name: str
    message_count: int
    
    class Config:
        from_attributes = True


class QuestionsListResponse(BaseModel):
    questions: List[QuestionResponse]
    total: int
    page: int
    limit: int
    pages: int


class AnswerRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ConsultationStats(BaseModel):
    pending_count: int
    in_progress_count: int
    completed_today: int
    avg_response_time_minutes: float


# Helper functions
async def get_questions_query(status_filter: Optional[str] = None):
    """Build base query for questions with filters"""
    query = select(Question).options(
        selectinload(Question.user),
        selectinload(Question.messages)
    )
    
    if status_filter:
        query = query.where(Question.status == status_filter)
    
    return query.order_by(Question.created_at.desc())


# Routes
@router.get("/questions", response_model=QuestionsListResponse)
async def get_questions(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get list of questions with filtering and pagination"""
    
    # Get total count
    count_query = select(func.count()).select_from(Question)
    if status:
        count_query = count_query.where(Question.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated questions
    query = await get_questions_query(status)
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    # Convert to response format
    questions_data = []
    for q in questions:
        user_name = f"{q.user.first_name or ''} {q.user.last_name or ''}".strip()
        if not user_name:
            user_name = f"User {q.user.telegram_id}"
        
        questions_data.append(QuestionResponse(
            uuid=str(q.uuid),
            text=str(q.text),
            status=str(q.status),
            created_at=q.created_at,
            updated_at=q.updated_at,
            user_name=user_name,
            message_count=len(q.dialog_messages),
        ))
    
    pages = (total + limit - 1) // limit if limit > 0 else 0
    
    return QuestionsListResponse(
        questions=questions_data,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/questions/{question_id}")
async def get_question_by_id(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get single question with full details and message history"""
    
    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID")
    
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.user),
            selectinload(Question.messages)
        )
        .where(Question.uuid == question_uuid)
    )
    
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Format messages
    messages = []
    for msg in question.dialog_messages:
        sender_type = "user" if msg.sender_type == "user" else "pharmacist"
        sender_name = question.user.first_name if sender_type == "user" else "Фармацевт"
        
        messages.append({
            "id": str(msg.uuid),
            "text": msg.text,
            "sender_type": sender_type,
            "sender_name": sender_name,
            "created_at": msg.created_at,
            "message_type": msg.message_type,
        })
    
    return {
        "uuid": str(question.uuid),
        "text": question.text,
        "status": question.status,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "user": {
            "name": f"{question.user.first_name or ''} {question.user.last_name or ''}".strip(),
            "telegram_id": question.user.telegram_id,
        },
        "messages": messages,
    }


@router.post("/questions/{question_id}/answer")
async def answer_question(
    question_id: str,
    answer_data: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Send answer to user's question"""
    
    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID")
    
    result = await db.execute(
        select(Question).where(Question.uuid == question_uuid)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    if question.status == "completed":
        raise HTTPException(
            status_code=400, 
            detail="Cannot answer to completed question"
        )
    
    # Create message in dialog history
    new_message = DialogMessage(
        question_id=question.uuid,
        sender_type="pharmacist",
        sender_id=pharmacist.uuid,
        message_type="answer",
        text=answer_data.text,
    )
    
    db.add(new_message)
    
    # Update question status
    question.status = "answered"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # TODO: Send notification to user via Telegram Bot
    # This will be handled by background task or WebSocket
    
    logger.info(f"Pharmacist {pharmacist.uuid} answered question {question_id}")
    
    return {"message": "Answer sent successfully"}


@router.put("/questions/{question_id}/complete")
async def complete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Complete/close consultation"""
    
    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID")
    
    result = await db.execute(
        select(Question).where(Question.uuid == question_uuid)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question.status = "completed"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Pharmacist {pharmacist.uuid} completed question {question_id}")
    
    return {"message": "Question completed"}


@router.post("/questions/{question_id}/assign")
async def assign_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Assign question to current pharmacist"""
    
    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID")
    
    result = await db.execute(
        select(Question).where(Question.uuid == question_uuid)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question.taken_by = pharmacist.uuid
    question.status = "in_progress"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Pharmacist {pharmacist.uuid} assigned question {question_id}")
    
    return {"message": "Question assigned successfully"}


@router.get("/questions/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get count of unread/new questions"""
    
    result = await db.execute(
        select(func.count()).where(Question.status == "pending")
    )
    count = result.scalar() or 0
    
    return {"count": count}


@router.get("/consultations/stats", response_model=ConsultationStats)
async def get_consultation_stats(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get consultation statistics"""
    
    # Pending count
    pending_result = await db.execute(
        select(func.count()).where(Question.status == "pending")
    )
    pending_count = pending_result.scalar() or 0
    
    # In progress count
    in_progress_result = await db.execute(
        select(func.count()).where(Question.status == "in_progress")
    )
    in_progress_count = in_progress_result.scalar() or 0
    
    # Completed today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_result = await db.execute(
        select(func.count()).where(
            and_(
                Question.status == "completed",
                Question.updated_at >= today_start
            )
        )
    )
    completed_today = completed_result.scalar() or 0
    
    # Average response time (simplified - last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    avg_time_result = await db.execute(
        select(func.avg(Question.updated_at - Question.created_at)).where(
            and_(
                Question.status.in_(["answered", "completed"]),
                Question.created_at >= week_ago
            )
        )
    )
    avg_time = avg_time_result.scalar()
    avg_response_time = (avg_time.total_seconds() / 60) if avg_time else 0
    
    return ConsultationStats(
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_today=completed_today,
        avg_response_time_minutes=round(avg_response_time, 2),
    )


# WebSocket endpoint for real-time updates
@router.websocket("/ws/pharmacist")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """WebSocket connection for real-time consultation updates"""
    
    await websocket.accept()
    
    try:
        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            # For now, just keep connection alive
            
    except WebSocketDisconnect:
        logger.info("Pharmacist WebSocket disconnected")
