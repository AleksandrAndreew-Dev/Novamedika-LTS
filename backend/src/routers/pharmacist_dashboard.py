"""Router for Pharmacist WebApp Dashboard - Consultations Management"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    Body,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Set, Dict
import uuid
from datetime import datetime, timedelta
import logging

from db.database import get_db, async_session_maker
from db.qa_models import Question, User, Pharmacist, DialogMessage
from auth.session_auth import get_current_pharmacist_session as get_current_pharmacist
from auth.session_manager import get_pharmacist_by_session
from pydantic import BaseModel, Field
from utils.time_utils import get_utc_now_naive
import asyncio
import json
import redis.asyncio as aioredis
from auth.session_manager import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Pharmacist Dashboard"],
)


class WebSocketConnectionManager:
    """Manage WebSocket connections for pharmacist dashboard"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = (
            {}
        )  # question_id -> set of WebSockets

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        # Also remove from user_connections
        for qid in list(self.user_connections.keys()):
            self.user_connections[qid].discard(websocket)
            if not self.user_connections[qid]:
                del self.user_connections[qid]

    async def connect_user(self, websocket: WebSocket, question_id: str):
        """Connect a user WebSocket for a specific consultation"""
        await websocket.accept()
        self.active_connections.add(websocket)
        if question_id not in self.user_connections:
            self.user_connections[question_id] = set()
        self.user_connections[question_id].add(websocket)

    def disconnect_user(self, websocket: WebSocket, question_id: str = None):
        self.active_connections.discard(websocket)
        if question_id and question_id in self.user_connections:
            self.user_connections[question_id].discard(websocket)
            if not self.user_connections[question_id]:
                del self.user_connections[question_id]
        else:
            # Try to find in all user_connections
            for qid in list(self.user_connections.keys()):
                self.user_connections[qid].discard(websocket)
                if not self.user_connections[qid]:
                    del self.user_connections[qid]

    async def broadcast(self, message: dict):
        """Send message to all connected pharmacists (not users)"""
        disconnected = set()
        for connection in self.active_connections:
            if connection in self._all_user_websockets():
                continue
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)

    def _all_user_websockets(self) -> Set[WebSocket]:
        """Get all user WebSockets across all consultations"""
        result = set()
        for sockets in self.user_connections.values():
            result.update(sockets)
        return result

    async def broadcast_to_consultation(self, question_id: str, message: dict):
        """Send message to all WebSockets subscribed to a specific consultation"""
        disconnected = set()
        # Send to user connections for this question
        if question_id in self.user_connections:
            for conn in self.user_connections[question_id]:
                try:
                    await conn.send_json(message)
                except Exception:
                    disconnected.add(conn)
            for conn in disconnected:
                self.user_connections[question_id].discard(conn)
                self.active_connections.discard(conn)
                if not self.user_connections[question_id]:
                    del self.user_connections[question_id]

    async def broadcast_new_question(self, question_data: dict):
        """Broadcast new question notification to all connected pharmacists"""
        await self.broadcast({"type": "new_question", "data": question_data})

    async def broadcast_message_update(self, question_id: str, message_data: dict):
        """Broadcast new message in consultation to pharmacists AND subscribed users"""
        # Send to pharmacists
        await self.broadcast(
            {"type": "message_update", "question_id": question_id, "data": message_data}
        )
        # Send to user subscribed to this consultation
        await self.broadcast_to_consultation(
            question_id,
            {
                "type": "message_update",
                "question_id": question_id,
                "data": message_data,
            },
        )


# Redis Pub/Sub channel for cross-worker WebSocket sync
REDIS_WS_CHANNEL = "ws:pharmacist:events"


async def publish_to_redis(message: dict):
    """Publish event to Redis Pub/Sub channel for cross-worker sync"""
    try:
        r = await get_redis_client()
        await r.publish(REDIS_WS_CHANNEL, json.dumps(message, default=str))
    except Exception as e:
        logger.warning(f"Redis publish failed (non-critical): {e}")


async def redis_ws_listener():
    """Background task: listen to Redis Pub/Sub and broadcast locally"""
    while True:
        try:
            r = await get_redis_client()
            pubsub = r.pubsub()
            await pubsub.subscribe(REDIS_WS_CHANNEL)
            logger.info("Redis WS listener started")
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        event_type = data.get("type", "")
                        if event_type == "message_update":
                            await ws_manager.broadcast_message_update(
                                data.get("question_id", ""),
                                data.get("message_data", {}),
                            )
                        elif event_type == "new_question":
                            await ws_manager.broadcast_new_question(
                                data.get("question_data", {})
                            )
                        elif event_type == "question_assigned":
                            await ws_manager.broadcast(data)
                        else:
                            await ws_manager.broadcast(data)
                    except Exception as e:
                        logger.warning(f"Redis WS message parse error: {e}")
        except Exception as e:
            logger.error(f"Redis WS listener error: {e}, restarting in 5s")
            await asyncio.sleep(5)


# Global WebSocket manager instance
ws_manager = WebSocketConnectionManager()
# Global reference for the listener task
_redis_listener_task = None


def start_redis_listener():
    """Start the Redis Pub/Sub listener background task"""
    global _redis_listener_task
    if _redis_listener_task is None or _redis_listener_task.done():
        _redis_listener_task = asyncio.create_task(redis_ws_listener())
        logger.info("Redis WS listener task started")


def stop_redis_listener():
    """Stop the Redis Pub/Sub listener background task"""
    global _redis_listener_task
    if _redis_listener_task and not _redis_listener_task.done():
        _redis_listener_task.cancel()
        logger.info("Redis WS listener task stopped")


# Pydantic Schemas
class QuestionResponse(BaseModel):
    uuid: str
    text: str
    status: str
    created_at: datetime
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
        selectinload(Question.user), selectinload(Question.dialog_messages)
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

    # Map frontend filter values to DB status values
    db_status_map = {
        "new": "pending",
        "in_progress": "in_progress",
        "answered": "answered",
        "completed": "completed",
        "pending": "pending",
    }
    db_status = db_status_map.get(status, status) if status else None

    # Get total count
    count_query = select(func.count()).select_from(Question)
    if db_status:
        count_query = count_query.where(Question.status == db_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated questions
    query = await get_questions_query(db_status)
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    questions = result.scalars().all()

    # Convert to response format
    questions_data = []
    for q in questions:
        user_name = f"{q.user.first_name or ''} {q.user.last_name or ''}".strip()
        if not user_name:
            user_name = f"User {q.user.telegram_id}"

        questions_data.append(
            QuestionResponse(
                uuid=str(q.uuid),
                text=str(q.text),
                status=str(q.status),
                created_at=q.created_at,
                user_name=user_name,
                message_count=len(q.dialog_messages),
            )
        )

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
        .options(selectinload(Question.user), selectinload(Question.dialog_messages))
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

        messages.append(
            {
                "id": str(msg.uuid),
                "text": msg.text,
                "sender_type": sender_type,
                "sender_name": sender_name,
                "created_at": msg.created_at,
                "message_type": msg.message_type,
            }
        )

    return {
        "uuid": str(question.uuid),
        "text": question.text,
        "status": question.status,
        "created_at": question.created_at,
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

    result = await db.execute(select(Question).where(Question.uuid == question_uuid))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == "completed":
        raise HTTPException(
            status_code=400, detail="Cannot answer to completed question"
        )

    # Create message in dialog history
    new_message = DialogMessage(
        uuid=uuid.uuid4(),
        question_id=question.uuid,
        sender_type="pharmacist",
        sender_id=pharmacist.uuid,
        message_type="answer",
        text=answer_data.text,
    )

    db.add(new_message)

    # Update question status
    question.status = "answered"

    await db.commit()
    await db.refresh(new_message)

    # 1. WebSocket broadcast (pharmacists + subscribed user)
    ws_msg_data = {
        "question_id": str(question.uuid),
        "message_data": {
            "uuid": str(new_message.uuid),
            "question_id": str(new_message.question_id),
            "sender_type": "pharmacist",
            "text": new_message.text,
            "created_at": new_message.created_at.isoformat(),
        },
    }
    try:
        await ws_manager.broadcast_message_update(**ws_msg_data)
        logger.info(f"WebSocket broadcast sent for answer to {question_id}")
    except Exception as e:
        logger.warning(f"WebSocket broadcast failed (non-critical): {e}")
    # Publish to Redis for cross-worker sync
    asyncio.ensure_future(publish_to_redis({"type": "message_update", **ws_msg_data}))

    # 2. Telegram notification to user (if user has telegram_id)
    try:
        from bot.core import bot_manager

        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            bot, _ = await bot_manager.initialize()
            if bot:
                pharmacy_info = pharmacist.pharmacy_info or {}
                chain = pharmacy_info.get("chain", "")
                number = pharmacy_info.get("number", "")
                first_name = pharmacy_info.get("first_name", "")
                last_name = pharmacy_info.get("last_name", "")

                pharmacist_name_parts = []
                if last_name:
                    pharmacist_name_parts.append(last_name)
                if first_name:
                    pharmacist_name_parts.append(first_name)
                pharmacist_name = (
                    " ".join(pharmacist_name_parts)
                    if pharmacist_name_parts
                    else "Фармацевт"
                )

                location = ""
                if chain and number:
                    location = f", {chain}, аптека №{number}"

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

                user_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✍️ Ответить",
                                callback_data=f"continue_user_dialog_{question.uuid}",
                            ),
                            InlineKeyboardButton(
                                text="✅ Завершить",
                                callback_data=f"end_dialog_{question.uuid}",
                            ),
                        ]
                    ]
                )

                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"💬 <b>Ответ фармацевта</b>\n\n"
                        f"{answer_data.text}\n\n"
                        f"👨‍⚕️ <i>{pharmacist_name}{location}</i>"
                    ),
                    parse_mode="HTML",
                    reply_markup=user_keyboard,
                )
                logger.info(f"Telegram notification sent to user {user.telegram_id}")
    except Exception as e:
        logger.warning(f"Telegram notification failed (non-critical): {e}")

    logger.info(f"Pharmacist {pharmacist.uuid} answered question {question_id}")

    return {"message": "Answer sent successfully", "uuid": str(new_message.uuid)}


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

    result = await db.execute(select(Question).where(Question.uuid == question_uuid))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.status = "completed"

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

    result = await db.execute(select(Question).where(Question.uuid == question_uuid))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.taken_by = pharmacist.uuid
    question.status = "in_progress"

    await db.commit()

    logger.info(f"Pharmacist {pharmacist.uuid} assigned question {question_id}")

    # Broadcast to all pharmacists that this question has been taken
    assign_data = {
        "type": "question_assigned",
        "question_id": question_id,
        "assigned_to": str(pharmacist.uuid),
    }
    try:
        await ws_manager.broadcast(assign_data)
        logger.info(f"Assignment broadcast sent for {question_id}")
    except Exception as e:
        logger.warning(f"Assignment broadcast failed (non-critical): {e}")
    # Publish to Redis for cross-worker sync
    asyncio.ensure_future(publish_to_redis(assign_data))

    return {"message": "Question assigned successfully"}


@router.get("/questions/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get count of unread/new questions"""

    result = await db.execute(select(func.count()).where(Question.status == "pending"))
    count = result.scalar() or 0

    return {"count": count}


@router.get("/consultations/stats", response_model=ConsultationStats)
async def get_consultation_stats(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get consultation statistics"""

    pending_result = await db.execute(
        select(func.count()).where(Question.status == "pending")
    )
    pending_count = pending_result.scalar() or 0

    in_progress_result = await db.execute(
        select(func.count()).where(Question.status == "in_progress")
    )
    in_progress_count = in_progress_result.scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_result = await db.execute(
        select(func.count()).where(
            and_(Question.status == "completed", Question.created_at >= today_start)
        )
    )
    completed_today = completed_result.scalar() or 0

    week_ago = datetime.utcnow() - timedelta(days=7)
    avg_time_result = await db.execute(
        select(func.avg(Question.answered_at - Question.created_at)).where(
            and_(
                Question.status.in_(["answered", "completed"]),
                Question.created_at >= week_ago,
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


@router.put("/online")
async def update_online_status(
    online: bool = Body(..., embed=True),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Update pharmacist online status"""
    pharmacist.is_online = online
    pharmacist.last_seen = datetime.utcnow()
    await db.commit()
    return {"status": "ok", "is_online": online}


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class DialogMessageResponse(BaseModel):
    uuid: str
    question_id: str
    sender_type: str
    sender_id: str
    message_type: str
    text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get(
    "/questions/{question_id}/dialog", response_model=List[DialogMessageResponse]
)
async def get_dialog(
    question_id: str,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Get dialog messages for a specific question"""
    question_result = await db.execute(
        select(Question).where(Question.uuid == question_id)
    )
    question = question_result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_assigned = (
        question.assigned_to == pharmacist.uuid or question.taken_by == pharmacist.uuid
    )
    if not is_assigned:
        if question.status == "pending":
            question.taken_by = pharmacist.uuid
            question.assigned_to = pharmacist.uuid
            question.status = "in_progress"
            question.taken_at = datetime.utcnow()

            await db.commit()
            logger.info(
                f"Pharmacist {pharmacist.uuid} auto-assigned question {question_id}"
            )
        else:
            raise HTTPException(status_code=403, detail="Not assigned to this question")

    messages_result = await db.execute(
        select(DialogMessage)
        .where(DialogMessage.question_id == question_id)
        .order_by(DialogMessage.created_at)
    )
    messages = messages_result.scalars().all()

    # Convert UUIDs to strings for Pydantic validation
    return [
        DialogMessageResponse(
            uuid=str(msg.uuid),
            question_id=str(msg.question_id),
            sender_type=msg.sender_type,
            sender_id=str(msg.sender_id),
            message_type=msg.message_type,
            text=msg.text,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@router.post("/questions/{question_id}/dialog", response_model=DialogMessageResponse)
async def send_message(
    question_id: str,
    data: SendMessageRequest,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Send message in consultation dialog (from Web App)"""
    from main import app

    question_result = await db.execute(
        select(Question).where(Question.uuid == question_id)
    )
    question = question_result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_assigned = (
        question.assigned_to == pharmacist.uuid or question.taken_by == pharmacist.uuid
    )
    if not is_assigned:
        if question.status == "pending":
            question.taken_by = pharmacist.uuid
            question.assigned_to = pharmacist.uuid
            question.status = "in_progress"
            question.taken_at = datetime.utcnow()

            logger.info(
                f"Pharmacist {pharmacist.uuid} auto-assigned question {question_id} via send_message"
            )
        else:
            raise HTTPException(status_code=403, detail="Not assigned to this question")

    msg = DialogMessage(
        uuid=uuid.uuid4(),
        question_id=question_id,
        sender_type="pharmacist",
        sender_id=pharmacist.uuid,
        message_type="answer",
        text=data.text,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.flush()

    # Broadcast via WebSocket
    ws_msg_data = {
        "question_id": str(question_id),
        "message_data": {
            "uuid": str(msg.uuid),
            "question_id": str(question_id),
            "sender_type": "pharmacist",
            "sender_id": str(pharmacist.uuid),
            "text": data.text,
            "created_at": msg.created_at.isoformat(),
        },
    }
    try:
        await ws_manager.broadcast_message_update(**ws_msg_data)
    except Exception as ws_err:
        logger.warning(f"WebSocket broadcast failed (non-critical): {ws_err}")
    # Publish to Redis for cross-worker sync
    asyncio.ensure_future(publish_to_redis({"type": "message_update", **ws_msg_data}))

    await db.commit()
    await db.refresh(msg)

    # Send to user via Telegram bot
    try:
        bot = app.state.bot
        user_result = await db.execute(
            select(User).where(User.uuid == question.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user and user.telegram_id:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"💊 *Ответ фармацевта:*\n{data.text}",
                        parse_mode="Markdown",
                    )
                    break
                except Exception as retry_err:
                    if attempt < max_retries - 1:
                        wait = 2**attempt
                        logger.warning(
                            f"Retry {attempt+1}/{max_retries} sending bot message in {wait}s: {retry_err}"
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            f"Failed to send message to user after {max_retries} retries: {retry_err}"
                        )
    except Exception as e:
        logger.error(f"Failed to send message to user via bot (setup): {e}")

    return DialogMessageResponse(
        uuid=str(msg.uuid),
        question_id=str(msg.question_id),
        sender_type=msg.sender_type,
        sender_id=str(msg.sender_id),
        message_type=msg.message_type,
        text=msg.text,
        created_at=msg.created_at,
    )


# WebSocket for pharmacist dashboard
@router.websocket("/ws/pharmacist")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """WebSocket connection for real-time consultation updates.

    Authentication: accepts session token via query parameter `token`.
    If token is invalid or missing, connection is still accepted for
    backward compatibility, but client should provide token for full access.
    """
    # Authenticate via query parameter token
    authenticated = False
    pharmacist_uuid = None
    if token:
        try:
            async with async_session_maker() as db:
                pharmacist = await get_pharmacist_by_session(token, db)
                if pharmacist:
                    authenticated = True
                    pharmacist_uuid = str(pharmacist.uuid)
                    logger.info(
                        f"WebSocket authenticated for pharmacist {pharmacist_uuid}"
                    )
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")

    if not authenticated:
        logger.info("WebSocket connecting without authentication (limited mode)")

    await ws_manager.connect(websocket)
    logger.info(
        f"Pharmacist WebSocket connected (auth={authenticated}). "
        f"Total: {len(ws_manager.active_connections)}"
    )
    try:
        while True:
            data = await websocket.receive_text()
            # Handle auth command from client
            if data and data.startswith("auth:"):
                auth_token = data[5:].strip()
                async with async_session_maker() as db:
                    pharmacist = await get_pharmacist_by_session(auth_token, db)
                    if pharmacist:
                        authenticated = True
                        pharmacist_uuid = str(pharmacist.uuid)
                        await websocket.send_json(
                            {"type": "auth_ok", "pharmacist_id": str(pharmacist.uuid)}
                        )
                        logger.info(
                            f"WebSocket authenticated via command for pharmacist {pharmacist.uuid}"
                        )
                    else:
                        await websocket.send_json(
                            {"type": "auth_error", "detail": "Invalid session token"}
                        )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(
            f"Pharmacist WebSocket disconnected. Total: {len(ws_manager.active_connections)}"
        )
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"Pharmacist WebSocket error: {e}")
