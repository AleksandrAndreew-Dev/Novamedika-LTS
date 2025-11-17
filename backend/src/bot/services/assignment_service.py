# services/assignment_service.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.qa_models import Pharmacist, Question

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
