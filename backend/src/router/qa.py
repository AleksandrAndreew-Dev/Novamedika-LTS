from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from db.database import get_db
from db.qa_models import User, Question, Answer, Pharmacist
from db.qa_schemas import QuestionCreate, QuestionResponse, AnswerBase, AnswerResponse, PharmacistBasicResponse, UserResponse
from auth.auth import get_current_pharmacist

router = APIRouter()

@router.post("/questions/", response_model=QuestionResponse)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание вопроса от пользователя Telegram"""
    try:
        # Находим или создаем пользователя
        user_result = await db.execute(
            select(User).where(User.telegram_id == question.telegram_user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            user = User(
                uuid=uuid.uuid4(),
                telegram_id=question.telegram_user_id
            )
            db.add(user)
            await db.flush()

        # Проверяем родительский вопрос, если указан
        if question.parent_question_id:
            parent_result = await db.execute(
                select(Question).where(Question.uuid == question.parent_question_id)
            )
            parent_question = parent_result.scalar_one_or_none()
            if not parent_question:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Родительский вопрос не найден"
                )

        # Создаем вопрос
        new_question = Question(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            text=question.text,
            parent_question_id=question.parent_question_id,
            status='pending'
        )

        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Загружаем связанные данные для ответа
        await db.refresh(user)

        return QuestionResponse(
            uuid=new_question.uuid,
            text=new_question.text,
            status=new_question.status,
            created_at=new_question.created_at,
            user=UserResponse(
                uuid=user.uuid,
                first_name=user.first_name,
                last_name=user.last_name,
                telegram_username=user.telegram_username
            ),
            answers=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании вопроса: {str(e)}"
        )

@router.get("/questions/", response_model=List[QuestionResponse])
async def get_questions(
    status: Optional[str] = None,
    pharmacist_id: Optional[str] = None,
    pharmacy_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Question).options(
            selectinload(Question.user),
            selectinload(Question.assigned_pharmacist).selectinload(Pharmacist.user),
            selectinload(Question.answered_by_rel).selectinload(Pharmacist.user),
            selectinload(Question.answers).selectinload(Answer.pharmacist).selectinload(Pharmacist.user)
        )

        if status:
            query = query.where(Question.status == status)

        if pharmacist_id:
            query = query.where(
                or_(
                    Question.assigned_to == uuid.UUID(pharmacist_id),
                    Question.answered_by == uuid.UUID(pharmacist_id)
                )
            )

        # Фильтрация по аптеке
        if pharmacy_id:
            query = query.where(
                or_(
                    Question.assigned_to.in_(
                        select(Pharmacist.uuid).where(Pharmacist.pharmacy_id == uuid.UUID(pharmacy_id))
                    ),
                    Question.answered_by.in_(
                        select(Pharmacist.uuid).where(Pharmacist.pharmacy_id == uuid.UUID(pharmacy_id))
                    )
                )
            )

        result = await db.execute(query)
        questions = result.scalars().all()

        response = []
        for question in questions:
            answers_response = []
            for answer in question.answers:
                answers_response.append(AnswerResponse(
                    uuid=answer.uuid,
                    text=answer.text,
                    created_at=answer.created_at,
                    pharmacist=PharmacistBasicResponse(
                        uuid=answer.pharmacist.uuid,
                        user=UserResponse(
                            uuid=answer.pharmacist.user.uuid,
                            first_name=answer.pharmacist.user.first_name,
                            last_name=answer.pharmacist.user.last_name,
                            telegram_username=answer.pharmacist.user.telegram_username
                        )
                    )
                ))

            # Формируем информацию о назначенном фармацевте
            assigned_pharmacist = None
            if question.assigned_pharmacist:
                assigned_pharmacist = PharmacistBasicResponse(
                    uuid=question.assigned_pharmacist.uuid,
                    user=UserResponse(
                        uuid=question.assigned_pharmacist.user.uuid,
                        first_name=question.assigned_pharmacist.user.first_name,
                        last_name=question.assigned_pharmacist.user.last_name,
                        telegram_username=question.assigned_pharmacist.user.telegram_username
                    )
                )

            # Формируем информацию о фармацевте, ответившем на вопрос
            answered_by = None
            if question.answered_by_rel:
                answered_by = PharmacistBasicResponse(
                    uuid=question.answered_by_rel.uuid,
                    user=UserResponse(
                        uuid=question.answered_by_rel.user.uuid,
                        first_name=question.answered_by_rel.user.first_name,
                        last_name=question.answered_by_rel.user.last_name,
                        telegram_username=question.answered_by_rel.user.telegram_username
                    )
                )

            response.append(QuestionResponse(
                uuid=question.uuid,
                text=question.text,
                status=question.status,
                created_at=question.created_at,
                user=UserResponse(
                    uuid=question.user.uuid,
                    first_name=question.user.first_name,
                    last_name=question.user.last_name,
                    telegram_username=question.user.telegram_username
                ),
                assigned_to=assigned_pharmacist,
                answered_by=answered_by,
                answers=answers_response
            ))

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении вопросов: {str(e)}"
        )

@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
async def answer_question(
    question_id: str,
    answer: AnswerBase,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db)
):
    """Ответ фармацевта на вопрос"""
    try:
        # Проверяем существование вопроса
        question_result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = question_result.scalar_one_or_none()

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вопрос не найден"
            )

        # Создаем ответ с pharmacist_id из JWT токена
        new_answer = Answer(
            uuid=uuid.uuid4(),
            question_id=question.uuid,
            pharmacist_id=pharmacist.uuid,
            text=answer.text
        )

        # Обновляем статус вопроса
        question.status = 'answered'
        question.answered_by = pharmacist.uuid
        question.answered_at = datetime.now(timezone.utc)

        db.add(new_answer)
        await db.commit()
        await db.refresh(new_answer)

        return AnswerResponse(
            uuid=new_answer.uuid,
            text=new_answer.text,
            created_at=new_answer.created_at,
            pharmacist=PharmacistBasicResponse(
                uuid=pharmacist.uuid,
                user=UserResponse(
                    uuid=pharmacist.user.uuid,
                    first_name=pharmacist.user.first_name,
                    last_name=pharmacist.user.last_name,
                    telegram_username=pharmacist.user.telegram_username
                )
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании ответа: {str(e)}"
        )

@router.put("/questions/{question_id}/assign")
async def assign_question_to_me(
    question_id: str,
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(get_db)
):
    """Фармацевт назначает вопрос себе"""
    try:
        question_result = await db.execute(
            select(Question).where(Question.uuid == uuid.UUID(question_id))
        )
        question = question_result.scalar_one_or_none()

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вопрос не найден"
            )

        question.assigned_to = pharmacist.uuid
        await db.commit()

        return {"status": "success", "message": "Вопрос назначен вам"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при назначении вопроса: {str(e)}"
        )
