from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from db.database import get_db
from db.qa_models import User, Question, Answer, Pharmacist
from db.qa_schemas import QuestionCreate, QuestionResponse, AnswerBase, AnswerResponse
from auth.auth import get_current_pharmacist

router = APIRouter()

# В routers/qa.py добавить:
async def answer_question_internal(
    question_id: str,
    answer: AnswerBase,
    pharmacist: Pharmacist,
    db: AsyncSession
) -> AnswerResponse:
    """Внутренняя функция для ответа на вопрос (используется ботом)"""
    try:
        result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        new_answer = Answer(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            text=answer.text
        )

        question.status = 'answered'
        question.answered_by = pharmacist.uuid

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        return AnswerResponse.model_validate(new_answer)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании ответа: {str(e)}"
        )

# Вспомогательные функции
async def get_or_create_user(telegram_data: dict, db: AsyncSession) -> User:
    """Найти или создать пользователя"""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_data["telegram_user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            uuid=uuid.uuid4(),
            telegram_id=telegram_data["telegram_user_id"],
            first_name=telegram_data.get("first_name"),
            last_name=telegram_data.get("last_name"),
            telegram_username=telegram_data.get("telegram_username")
        )
        db.add(user)
        await db.flush()

    return user

async def get_user_by_telegram_id(telegram_id: int, db: AsyncSession) -> User:
    """Найти пользователя по Telegram ID"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Эндпоинты
@router.post("/questions/", response_model=QuestionResponse)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать вопрос"""
    try:
        user = await get_or_create_user(
            {
                "telegram_user_id": question.telegram_user_id,
                "first_name": None,
                "last_name": None,
                "telegram_username": None
            },
            db
        )

        new_question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=question.text,
            category=question.category,
            context_data=question.context_data
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
            detail=f"Ошибка при создании вопроса: {str(e)}"
        )

@router.get("/questions/", response_model=List[QuestionResponse])
async def get_questions(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить все вопросы (с фильтром по статусу)"""
    try:
        query = select(Question).options(
            selectinload(Question.user),
            selectinload(Question.assigned_pharmacist).selectinload(Pharmacist.user),
            selectinload(Question.answers).selectinload(Answer.pharmacist).selectinload(Pharmacist.user)
        )

        if status:
            query = query.where(Question.status == status)

        result = await db.execute(query)
        questions = result.scalars().all()

        # Используем model_validate вместо from_orm
        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопросов: {str(e)}"
        )

@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить вопрос по ID"""
    try:
        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.assigned_pharmacist).selectinload(Pharmacist.user),
                selectinload(Question.answers).selectinload(Answer.pharmacist).selectinload(Pharmacist.user)
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
            detail=f"Ошибка при получении вопроса: {str(e)}"
        )

# routers/qa.py - проверьте сигнатуру функции answer_question
@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
async def answer_question(
    question_id: str,
    answer: AnswerBase,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db)
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
            text=answer.text
        )

        # Обновляем статус вопроса
        question.status = 'answered'
        question.answered_by = pharmacist.uuid

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        return AnswerResponse.model_validate(new_answer)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании ответа: {str(e)}"
        )

@router.put("/questions/{question_id}/assign")
async def assign_question(
    question_id: str,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db)
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
            detail=f"Ошибка при назначении вопроса: {str(e)}"
        )

@router.get("/users/{telegram_id}/questions", response_model=List[QuestionResponse])
async def get_user_questions(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить вопросы пользователя"""
    try:
        user = await get_user_by_telegram_id(telegram_id, db)

        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.answers).selectinload(Answer.pharmacist).selectinload(Pharmacist.user)
            )
            .where(Question.user_id == user.uuid)
            .order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()

        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопросов: {str(e)}"
        )


@router.get("/pharmacist/questions", response_model=List[QuestionResponse])
async def get_pharmacist_questions(
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db)
):
    """Получить вопросы, назначенные текущему фармацевту"""
    try:
        result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.user),
                selectinload(Question.answers).selectinload(Answer.pharmacist).selectinload(Pharmacist.user)
            )
            .where(Question.assigned_to == pharmacist.uuid)
            .order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()
        return [QuestionResponse.model_validate(q) for q in questions]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении вопросов: {str(e)}")

@router.get("/questions/stats/")
async def get_questions_stats(db: AsyncSession = Depends(get_db)):
    """Статистика по вопросам"""
    try:
        # Общее количество вопросов
        total_result = await db.execute(select(Question))
        total = total_result.scalars().all()

        # Вопросы по статусам
        pending_result = await db.execute(select(Question).where(Question.status == "pending"))
        pending = pending_result.scalars().all()

        answered_result = await db.execute(select(Question).where(Question.status == "answered"))
        answered = answered_result.scalars().all()

        return {
            "total": len(total),
            "pending": len(pending),
            "answered": len(answered),
            "answer_rate": len(answered) / len(total) if total else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики: {str(e)}")


__all__ = ['router', 'answer_question_internal']
