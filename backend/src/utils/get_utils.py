from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload



from db.qa_models import Question, Pharmacist


async def get_all_pharmacist_questions(
    db: AsyncSession, pharmacist: Pharmacist, limit: int = 50
) -> List[Question]:
    """Получить все вопросы фармацевта с пагинацией"""
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.user))
        .where(Question.taken_by == pharmacist.uuid)
        .order_by(Question.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


