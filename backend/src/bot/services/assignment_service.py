# services/assignment_service.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.qa_models import Pharmacist, Question



# services/assignment_service.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from db.qa_models import Question, Pharmacist
from utils.time_utils import get_utc_now_naive

logger = logging.getLogger(__name__)


async def auto_assign_question(question, db: AsyncSession):
    """Автоматическое назначение вопроса свободному фармацевту"""
    try:
        # Находим фармацевта с наименьшим количеством назначенных вопросов
        result = await db.execute(
            select(Pharmacist)
            .join(Pharmacist.assigned_questions, isouter=True)
            .where(Pharmacist.is_active == True)
            .group_by(Pharmacist.uuid)
            .order_by(func.count(Question.uuid))
        )
        pharmacist = result.scalar_one_or_none()

        if pharmacist:
            question.assigned_to = pharmacist.uuid
            await db.commit()
            return pharmacist

        return None

    except Exception as e:
        logger.error(f"Error in auto assignment: {e}")
        return None



class QuestionAssignmentService:

    @staticmethod
    async def assign_question_to_pharmacist(
        question_id: str,
        pharmacist_id: str,
        db: AsyncSession
    ) -> bool:
        """Назначить вопрос конкретному фармацевту"""
        try:
            result = await db.execute(
                select(Question).where(Question.uuid == question_id)
            )
            question = result.scalar_one_or_none()

            if not question:
                logger.error(f"Question {question_id} not found")
                return False

            # Назначаем вопрос фармацевту
            question.taken_by = pharmacist_id
            question.taken_at = get_utc_now_naive()
            question.status = "in_progress"

            await db.commit()
            logger.info(f"Question {question_id} assigned to pharmacist {pharmacist_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning question: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def get_question_taker(
        question_id: str,
        db: AsyncSession
    ) -> Pharmacist | None:
        """Получить фармацевта, который взял вопрос"""
        try:
            result = await db.execute(
                select(Question)
                .options(selectinload(Question.taken_pharmacist))
                .where(Question.uuid == question_id)
            )
            question = result.scalar_one_or_none()

            return question.taken_pharmacist if question else None

        except Exception as e:
            logger.error(f"Error getting question taker: {e}")
            return None

    @staticmethod
    async def should_notify_all_pharmacists(
        question_id: str,
        db: AsyncSession
    ) -> bool:
        """Определить, нужно ли уведомлять всех фармацевтов"""
        try:
            # Проверяем, есть ли у вопроса назначенный фармацевт
            result = await db.execute(
                select(Question.taken_by).where(Question.uuid == question_id)
            )
            taken_by = result.scalar_one_or_none()

            # Если вопрос никто не взял, уведомляем всех
            return taken_by is None

        except Exception as e:
            logger.error(f"Error checking notification: {e}")
            return True  # В случае ошибки уведомляем всех
