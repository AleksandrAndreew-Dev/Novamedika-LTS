from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from db.database import get_db
from db.qa_models import User, Question, Answer, Pharmacist, DialogMessage
from db.qa_schemas import (
    QuestionCreate,
    QuestionResponse,
    UserResponse,
    AnswerBase,
    AnswerResponse,
)
from auth.auth import (
    get_current_pharmacist,
    get_current_user_jwt,
    get_current_user_jwt_or_tma,
)
from auth.security import get_api_key
from services.user_service import get_or_create_user
import logging
from sqlalchemy.orm import selectinload  # ДОБАВИТЬ

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def send_answer_to_user(question, answer_text: str, pharmacist, db: AsyncSession):
    """Отправка ответа пользователю в Telegram"""
    try:
        from bot.core import bot_manager

        # Используем уже инициализированный бот, не вызываем initialize() повторно
        if not bot_manager.bot:
            logger.error("Bot not initialized for sending answer to user")
            return

        bot = bot_manager.bot

        if question.user.telegram_id:
            message_text = (
                "💊 Получен ответ на ваш вопрос!\n\n"
                f"❓ Ваш вопрос: {question.text}\n\n"
                f"💬 Ответ фармацевта: {answer_text}\n\n"
                "Спасибо, что пользуйтесь нашим сервисом! ❤️"
            )

            await bot.send_message(chat_id=question.user.telegram_id, text=message_text)
            logger.info(f"Answer sent to user {question.user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send answer to user: {e}")


# Вспомогательные функции
async def get_user_by_telegram_id(telegram_id: int, db: AsyncSession) -> User:
    """Найти пользователя по Telegram ID"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Эндпоинты
@router.post("/questions/", response_model=QuestionResponse)
@limiter.limit("20/minute")
async def create_question(
    request: Request,
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Создать вопрос (rate limit 20/min)"""
    try:
        user = await get_or_create_user(
            db,
            telegram_id=question.telegram_user_id,
        )

        new_question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=question.text,
            category=question.category,
            context_data=question.context_data,
        )

        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Возвращаем данные с правильным преобразованием
        return QuestionResponse.model_validate(new_question)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании вопроса: {str(e)}",
        )


@router.get("/questions/", response_model=List[QuestionResponse])
async def get_questions(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Получить все вопросы (с фильтром по статусу)"""
    try:
        query = select(Question).options(
            selectinload(Question.user),
            selectinload(Question.assigned_pharmacist).selectinload(Pharmacist.user),
            selectinload(Question.answers)
            .selectinload(Answer.pharmacist)
            .selectinload(Pharmacist.user),
        )

        if status:
            query = query.where(Question.status == status)

        result = await db.execute(query)
        questions = result.scalars().all()

        # Используем model_validate вместо from_orm
        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        logger.warning(f"get_questions fallback (empty result) after error: {e}")
        return []  # ← Graceful fallback: пустой массив вместо 500


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Получить вопрос по ID"""
    try:
        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.assigned_pharmacist).selectinload(
                    Pharmacist.user
                ),
                selectinload(Question.answers)
                .selectinload(Answer.pharmacist)
                .selectinload(Pharmacist.user),
            )
            .where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        return QuestionResponse.model_validate(question)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопроса: {str(e)}",
        )


# routers/qa.py - проверьте сигнатуру функции answer_question
@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
async def answer_question(
    question_id: str,
    answer: AnswerBase,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Ответить на вопрос"""
    try:
        # Проверяем существование вопроса
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Создаем ответ
        new_answer = Answer(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            text=answer.text,
        )

        # Обновляем статус вопроса
        question.status = "answered"
        question.answered_by = pharmacist.uuid

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        return AnswerResponse.model_validate(new_answer)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании ответа: {str(e)}",
        )


@router.put("/questions/{question_id}/assign")
async def assign_question(
    question_id: str,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db),
):
    """Назначить вопрос себе"""
    try:
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        question.assigned_to = pharmacist.uuid
        await db.commit()

        return {"status": "success", "message": "Question assigned"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при назначении вопроса: {str(e)}",
        )


@router.get("/users/{telegram_id}/questions", response_model=List[QuestionResponse])
async def get_user_questions(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Получить вопросы пользователя"""
    try:
        user = await get_user_by_telegram_id(telegram_id, db)

        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.answers)
                .selectinload(Answer.pharmacist)
                .selectinload(Pharmacist.user),
            )
            .where(Question.user_id == user.uuid)
            .order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()

        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопросов: {str(e)}",
        )


# routers/qa.py - ДОПОЛНЕНИЯ

# router conflicts with dashboard
# @router.get("/pharmacist/questions", response_model=List[QuestionResponse])
# async def get_pharmacist_questions(
#     pharmacist: Pharmacist = Depends(get_current_pharmacist),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Получить вопросы, назначенные текущему фармацевту"""
#     try:
#         result = await db.execute(
#             select(Question)
#             .options(
#                 selectinload(Question.user),
#                 selectinload(Question.answers)
#                 .selectinload(Answer.pharmacist)
#                 .selectinload(Pharmacist.user),
#             )
#             .where(Question.assigned_to == pharmacist.uuid)
#             .order_by(Question.created_at.desc())
#         )
#         questions = result.scalars().all()
#         return [QuestionResponse.model_validate(q) for q in questions]

#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Ошибка при получении вопросов: {str(e)}"
#         )


@router.get("/questions/stats/")
async def get_questions_stats(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Статистика по вопросам"""
    try:
        # Общее количество вопросов
        total_result = await db.execute(select(Question))
        total = total_result.scalars().all()

        # Вопросы по статусам
        pending_result = await db.execute(
            select(Question).where(Question.status == "pending")
        )
        pending = pending_result.scalars().all()

        answered_result = await db.execute(
            select(Question).where(Question.status == "answered")
        )
        answered = answered_result.scalars().all()

        return {
            "total": len(total),
            "pending": len(pending),
            "answered": len(answered),
            "answer_rate": len(answered) / len(total) if total else 0,
        }

    except Exception as e:
        logger.warning(f"get_questions_stats fallback (zeros) after error: {e}")
        return {
            "total": 0,
            "pending": 0,
            "answered": 0,
            "answer_rate": 0,
        }  # ← Graceful fallback


# ============================================================================
# NEW CONSULTATION ENDPOINTS FOR WEB APP USERS (JWT AUTH)
# ============================================================================


class ConsultationCreate(BaseModel):
    """Модель для создания консультации"""

    text: str
    category: str = "general"
    context_data: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    """Модель для отправки сообщения"""

    text: str


class MessageResponse(BaseModel):
    """Модель ответа сообщения"""

    uuid: str
    question_id: str
    message_type: str
    sender_type: str
    sender_id: str
    text: Optional[str] = None
    file_id: Optional[str] = None
    caption: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsultationStats(BaseModel):
    """Модель статистики консультаций"""

    total_count: int
    pending_count: int
    answered_count: int
    completed_count: int


@router.post("/consultations/", response_model=QuestionResponse)
async def create_consultation(
    consultation: ConsultationCreate,
    current_user: User = Depends(get_current_user_jwt_or_tma),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую консультацию (JWT или TMA авторизация)

    Пользователь может создать вопрос/консультацию через веб-приложение
    или Telegram Web App.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация. Используйте /api/public/questions/ для анонимного доступа.",
        )

    try:
        new_question = Question(
            uuid=uuid.uuid4(),
            user_id=current_user.uuid,
            text=consultation.text,
            category=consultation.category,
            context_data=consultation.context_data,
            status="pending",
        )

        db.add(new_question)
        await db.flush()

        # Создаём начальное сообщение в диалоге
        initial_message = DialogMessage(
            uuid=uuid.uuid4(),
            question_id=new_question.uuid,
            sender_type="user",
            sender_id=current_user.uuid,
            message_type="question",
            text=consultation.text,
        )
        db.add(initial_message)
        await db.commit()
        await db.refresh(new_question)

        logger.info(
            f"New consultation created by user {current_user.uuid}: {new_question.uuid}"
        )

        # Explicit response - avoid MissingGreenlet in async context
        return QuestionResponse(
            uuid=new_question.uuid,
            text=new_question.text,
            status=new_question.status,
            category=new_question.category,
            created_at=new_question.created_at,
            user=UserResponse.model_validate(current_user),
            context_data=new_question.context_data,
            assigned_to=None,
            answered_by=None,
            answers=[],
        )

    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create consultation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании консультации: {str(e)}",
        )


@router.get("/consultations/", response_model=List[QuestionResponse])
async def get_user_consultations(
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """
    Получить список консультаций пользователя (требует JWT авторизации)

    Поддерживает пагинацию и фильтрацию по статусу.
    """
    try:
        query = (
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.assigned_pharmacist)
                .selectinload(Pharmacist.user)
                .selectinload(Pharmacist.pharmacy_info),
                selectinload(Question.answers)
                .selectinload(Answer.pharmacist)
                .selectinload(Pharmacist.user)
                .selectinload(Pharmacist.pharmacy_info),
            )
            .where(Question.user_id == current_user.uuid)
        )

        # Apply status filter if provided
        if status_filter:
            query = query.where(Question.status == status_filter)

        # Order by creation date (newest first)
        query = query.order_by(Question.created_at.desc())

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        questions = result.scalars().all()

        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        logger.exception("Failed to get user consultations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении консультаций: {str(e)}",
        )


@router.get("/consultations/{consultation_id}", response_model=QuestionResponse)
async def get_consultation_details(
    consultation_id: str,
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить детали консультации по ID (требует JWT авторизации)

    Проверяет, что консультация принадлежит текущему пользователю.
    """
    try:
        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.assigned_pharmacist).selectinload(
                    Pharmacist.user
                ),
                selectinload(Question.answers)
                .selectinload(Answer.pharmacist)
                .selectinload(Pharmacist.user),
                selectinload(Question.dialog_messages),
            )
            .where(Question.uuid == uuid.UUID(consultation_id))
            .where(
                Question.user_id == current_user.uuid
            )  # Security: only own consultations
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Консультация не найдена")

        return QuestionResponse.model_validate(question)

    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get consultation details")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении консультации: {str(e)}",
        )


@router.get("/consultations/stats", response_model=ConsultationStats)
async def get_consultation_stats(
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить статистику консультаций пользователя (требует JWT авторизации)
    """
    try:
        # Total count
        total_result = await db.execute(
            select(Question).where(Question.user_id == current_user.uuid)
        )
        total = total_result.scalars().all()

        # Pending count
        pending_result = await db.execute(
            select(Question).where(
                Question.user_id == current_user.uuid, Question.status == "pending"
            )
        )
        pending = pending_result.scalars().all()

        # Answered count
        answered_result = await db.execute(
            select(Question).where(
                Question.user_id == current_user.uuid, Question.status == "answered"
            )
        )
        answered = answered_result.scalars().all()

        # Completed count
        completed_result = await db.execute(
            select(Question).where(
                Question.user_id == current_user.uuid, Question.status == "completed"
            )
        )
        completed = completed_result.scalars().all()

        return ConsultationStats(
            total_count=len(total),
            pending_count=len(pending),
            answered_count=len(answered),
            completed_count=len(completed),
        )

    except Exception as e:
        logger.exception("Failed to get consultation stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики: {str(e)}",
        )


@router.get(
    "/consultations/{consultation_id}/messages", response_model=List[MessageResponse]
)
async def get_consultation_messages(
    consultation_id: str,
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить сообщения консультации (требует JWT авторизации)

    Возвращает историю диалога для конкретной консультации.
    """
    try:
        # First verify that consultation belongs to user
        result = await db.execute(
            select(Question).where(
                Question.uuid == uuid.UUID(consultation_id),
                Question.user_id == current_user.uuid,
            )
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Консультация не найдена")

        # Get dialog messages
        messages_result = await db.execute(
            select(DialogMessage)
            .where(DialogMessage.question_id == uuid.UUID(consultation_id))
            .where(DialogMessage.is_deleted == False)
            .order_by(DialogMessage.created_at.asc())
        )
        messages = messages_result.scalars().all()

        return [MessageResponse.model_validate(msg) for msg in messages]

    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get consultation messages")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении сообщений: {str(e)}",
        )


@router.post(
    "/consultations/{consultation_id}/messages", response_model=MessageResponse
)
async def send_consultation_message(
    consultation_id: str,
    message: MessageCreate,
    current_user: User = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Отправить сообщение в консультацию (требует JWT авторизации)

    Пользователь может отправить сообщение фармацевту в рамках консультации.
    После сохранения уведомление отправляется:
    - Через WebSocket в pharmacist dashboard
    - Через Telegram бот (если фармацевт найден)
    """
    try:
        # Verify consultation belongs to user
        result = await db.execute(
            select(Question).where(
                Question.uuid == uuid.UUID(consultation_id),
                Question.user_id == current_user.uuid,
            )
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Консультация не найдена")

        # Create new dialog message
        new_message = DialogMessage(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            message_type="question",
            sender_type="user",
            sender_id=current_user.uuid,
            text=message.text,
        )

        db.add(new_message)

        # Update question status if it was answered/completed
        if question.status in ["answered", "completed"]:
            question.status = "pending"  # Reopen for new question

        await db.commit()
        await db.refresh(new_message)

        # 1. WebSocket broadcast to pharmacist dashboard
        try:
            from routers.pharmacist_dashboard import ws_manager

            await ws_manager.broadcast_message_update(
                question_id=consultation_id,
                message_data={
                    "uuid": str(new_message.uuid),
                    "question_id": consultation_id,
                    "sender_type": "user",
                    "text": new_message.text,
                    "created_at": new_message.created_at.isoformat(),
                },
            )
            logger.info(
                f"WebSocket broadcast sent for user message in {consultation_id}"
            )
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast failed (non-critical): {ws_err}")

        # 2. Telegram notification to pharmacist (if assigned) with answer button
        try:
            pharmacist_id = question.taken_by or question.assigned_to
            if pharmacist_id:
                ph_result = await db.execute(
                    select(Pharmacist)
                    .options(selectinload(Pharmacist.user))
                    .where(Pharmacist.uuid == pharmacist_id)
                )
                pharmacist = ph_result.scalar_one_or_none()

                if pharmacist and pharmacist.user and pharmacist.user.telegram_id:
                    from bot.core import bot_manager
                    from bot.keyboards.qa_keyboard import make_question_keyboard

                    if bot_manager.bot:
                        bot = bot_manager.bot
                        user_name = f"{current_user.first_name or 'Пользователь'}"
                        if current_user.last_name:
                            user_name += f" {current_user.last_name}"

                        await bot.send_message(
                            chat_id=pharmacist.user.telegram_id,
                            text=(
                                f"💬 <b>Новое сообщение от {user_name}</b>\n\n"
                                f"{message.text}\n\n"
                            ),
                            parse_mode="HTML",
                            reply_markup=make_question_keyboard(consultation_id),
                        )
                        logger.info(
                            f"Telegram notification sent to pharmacist {pharmacist.user.telegram_id}"
                        )
        except Exception as tg_err:
            logger.warning(f"Telegram notification failed (non-critical): {tg_err}")

        logger.info(
            f"New message sent in consultation {consultation_id} by user {current_user.uuid}"
        )

        return MessageResponse.model_validate(new_message)

    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to send message")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отправке сообщения: {str(e)}",
        )


# ============================================================================
# PUBLIC ENDPOINTS (для анонимных пользователей без JWT)
# ============================================================================


class PublicQuestionCreate(BaseModel):
    """Модель для создания вопроса анонимным пользователем"""

    text: str
    category: str = "general"
    anon_user_id: Optional[str] = None  # UUID, генерируется на фронтенде


@router.post("/public/questions/")
async def create_public_question(
    question: PublicQuestionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать вопрос от анонимного пользователя (без JWT).

    Используется для веб-пользователей, которые не зарегистрированы
    и не находятся в Telegram. Создаёт временного пользователя.
    """
    try:
        anon_id = (
            uuid.uuid4()
            if not question.anon_user_id
            else uuid.UUID(question.anon_user_id)
        )

        # Создаём или находим анонимного пользователя по anon_user_id
        result = await db.execute(select(User).where(User.uuid == anon_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                uuid=anon_id,
                first_name="Гость",
                telegram_username=None,
                telegram_id=None,
                user_type="customer",
                consent_privacy_policy=True,
            )
            db.add(user)
            await db.flush()
            logger.info(f"Created anonymous user {anon_id}")

        # Создаём вопрос
        new_question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=question.text,
            category=question.category,
            status="pending",
        )

        db.add(new_question)
        await db.flush()

        # Создаём начальное сообщение в диалоге
        initial_message = DialogMessage(
            uuid=uuid.uuid4(),
            question_id=new_question.uuid,
            sender_type="user",
            sender_id=user.uuid,
            message_type="question",
            text=question.text,
        )
        db.add(initial_message)
        await db.commit()
        await db.refresh(new_question)

        logger.info(
            f"Public question created by anon user {user.uuid}: {new_question.uuid}"
        )

        # Broadcast to pharmacist dashboard via WebSocket
        try:
            from routers.pharmacist_dashboard import ws_manager

            await ws_manager.broadcast_new_question(
                {
                    "uuid": str(new_question.uuid),
                    "text": new_question.text,
                    "status": new_question.status,
                    "created_at": new_question.created_at.isoformat(),
                    "user_name": "Гость",
                    "message_count": 0,
                }
            )
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast failed (non-critical): {ws_err}")

        return {
            "uuid": str(new_question.uuid),
            "user_uuid": str(user.uuid),
            "text": new_question.text,
            "status": new_question.status,
            "created_at": new_question.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create public question")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании вопроса: {str(e)}",
        )


class PublicMessageCreate(BaseModel):
    """Модель для отправки сообщения анонимным пользователем"""

    text: str


@router.get("/public/questions/{question_id}")
async def get_public_question(
    question_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить вопрос анонимного пользователя (без JWT).

    Доступен только для вопросов, созданных через /api/public/questions/.
    """
    try:
        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.answers),
            )
            .where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")

        return {
            "uuid": str(question.uuid),
            "text": question.text,
            "status": question.status,
            "category": question.category,
            "created_at": question.created_at.isoformat(),
            "answers": [
                {
                    "uuid": str(a.uuid),
                    "text": a.text,
                    "created_at": a.created_at.isoformat(),
                }
                for a in question.answers
            ],
        }

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except Exception as e:
        logger.exception("Failed to get public question")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопроса: {str(e)}",
        )


@router.get("/public/questions/{question_id}/messages")
async def get_public_question_messages(
    question_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить сообщения анонимного пользователя (без JWT).
    """
    logger.info(f"Fetching public question messages for {question_id}")
    try:
        # Верифицируем, что вопрос существует
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")

        # Получаем сообщения диалога
        messages_result = await db.execute(
            select(DialogMessage)
            .where(DialogMessage.question_id == uuid.UUID(question_id))
            .where(DialogMessage.is_deleted == False)
            .order_by(DialogMessage.created_at.asc())
        )
        messages = messages_result.scalars().all()

        return [
            {
                "uuid": str(m.uuid),
                "question_id": str(m.question_id),
                "message_type": m.message_type,
                "sender_type": m.sender_type,
                "sender_id": str(m.sender_id),
                "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except Exception as e:
        logger.exception("Failed to get public question messages")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении сообщений: {str(e)}",
        )


@router.post("/public/questions/{question_id}/messages")
async def send_public_question_message(
    question_id: str,
    message: PublicMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Отправить сообщение в вопрос анонимного пользователя (без JWT).

    Используется для веб-пользователей, которые не авторизованы.
    """
    try:
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")

        # Создаём новое сообщение
        new_message = DialogMessage(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            message_type="question",
            sender_type="user",
            sender_id=question.user_id,
            text=message.text,
        )

        db.add(new_message)
        # Обновляем статус вопроса
        if question.status in ["answered", "completed"]:
            question.status = "pending"

        await db.commit()
        await db.refresh(new_message)

        # Broadcast via WebSocket to pharmacist dashboard
        try:
            from routers.pharmacist_dashboard import ws_manager

            await ws_manager.broadcast_message_update(
                question_id=question_id,
                message_data={
                    "uuid": str(new_message.uuid),
                    "question_id": question_id,
                    "sender_type": "user",
                    "text": new_message.text,
                    "created_at": new_message.created_at.isoformat(),
                },
            )
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast failed (non-critical): {ws_err}")

        # Telegram notification to available pharmacists with "Взять и ответить" button
        try:
            ph_result = await db.execute(
                select(Pharmacist)
                .options(selectinload(Pharmacist.user))
                .where(Pharmacist.is_active == True)
            )
            pharmacists = ph_result.scalars().all()

            if pharmacists:
                from bot.core import bot_manager
                from bot.keyboards.qa_keyboard import make_question_keyboard

                if bot_manager.bot:
                    bot = bot_manager.bot
                    for pharmacist in pharmacists:
                        if pharmacist.user and pharmacist.user.telegram_id:
                            try:
                                await bot.send_message(
                                    chat_id=pharmacist.user.telegram_id,
                                    text=(
                                        f"💬 <b>Новое сообщение от пользователя</b>\n\n"
                                        f"{message.text}\n\n"
                                    ),
                                    parse_mode="HTML",
                                    reply_markup=make_question_keyboard(question_id),
                                )
                            except Exception as tg_err:
                                logger.warning(
                                    f"Telegram notification to pharmacist {pharmacist.user.telegram_id} failed: {tg_err}"
                                )
                            logger.info(
                                f"Telegram notification sent to pharmacist {pharmacist.user.telegram_id}"
                            )
        except Exception as tg_err:
            logger.warning(
                f"Telegram notification to pharmacists failed (non-critical): {tg_err}"
            )

        # Send message back to user's Telegram chat if available
        try:
            if question.user and question.user.telegram_id:
                from bot.core import bot_manager

                if bot_manager.bot:
                    bot = bot_manager.bot
                    await bot.send_message(
                        chat_id=question.user.telegram_id,
                        text=message.text,
                    )
                    logger.info(
                        f"Message forwarded to user's Telegram chat {question.user.telegram_id}"
                    )
        except Exception as tg_err:
            logger.warning(
                f"Failed to send message to user's Telegram chat (non-critical): {tg_err}"
            )

        logger.info(f"New message in public question {question_id}")

        return {
            "uuid": str(new_message.uuid),
            "question_id": str(new_message.question_id),
            "message_type": new_message.message_type,
            "sender_type": new_message.sender_type,
            "sender_id": str(new_message.sender_id),
            "text": new_message.text,
            "created_at": new_message.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to send public question message")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отправке сообщения: {str(e)}",
        )


__all__ = ["router"]
