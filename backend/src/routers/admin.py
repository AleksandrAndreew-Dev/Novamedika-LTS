"""
Admin endpoints для управления системой и просмотра audit logs.
Требует ADMIN_API_KEY для доступа.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import uuid

from db.database import get_db
from db.models import AuditLog
from utils.auth import verify_admin_api_key

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
)


class AuditLogResponse(BaseModel):
    """Модель ответа для audit log"""
    id: str
    user_id: Optional[str] = None
    user_type: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    endpoint: str
    status_code: Optional[str] = None
    success: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogsListResponse(BaseModel):
    """Модель списка audit logs с пагинацией"""
    total: int
    logs: List[AuditLogResponse]
    page: int
    page_size: int


@router.get("/audit-logs", response_model=AuditLogsListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(50, ge=1, le=500, description="Размер страницы"),
    user_id: Optional[str] = Query(None, description="Фильтр по user_id"),
    user_type: Optional[str] = Query(None, description="Фильтр по типу пользователя"),
    action: Optional[str] = Query(None, description="Фильтр по действию (read/create/update/delete)"),
    resource_type: Optional[str] = Query(None, description="Фильтр по типу ресурса"),
    date_from: Optional[datetime] = Query(None, description="Начальная дата"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_api_key),
):
    """
    Получение логов аудита доступа к персональным данным.
    
    Требует ADMIN_API_KEY header.
    
    Параметры фильтрации:
    - user_id: UUID пользователя
    - user_type: тип пользователя (user/pharmacist/admin/system)
    - action: действие (read/create/update/delete/export)
    - resource_type: тип ресурса (user/pharmacist/order/question)
    - date_from/date_to: временной диапазон
    
    Возвращает пагинированный список событий аудита.
    """
    # Базовый запрос
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)
    
    # Применяем фильтры
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.where(AuditLog.user_id == user_uuid)
            count_query = count_query.where(AuditLog.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    if user_type:
        query = query.where(AuditLog.user_type == user_type)
        count_query = count_query.where(AuditLog.user_type == user_type)
    
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
        count_query = count_query.where(AuditLog.created_at >= date_from)
    
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
        count_query = count_query.where(AuditLog.created_at <= date_to)
    
    # Получаем общее количество
    result = await db.execute(count_query)
    total = result.scalar() or 0
    
    # Пагинация и сортировка
    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    
    # Выполняем запрос
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return AuditLogsListResponse(
        total=total,
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=365, description="Количество дней для статистики"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_api_key),
):
    """
    Статистика по audit logs за последние N дней.
    
    Возвращает:
    - Общее количество событий
    - Распределение по типам действий
    - Распределение по типам ресурсов
    - Топ-10 пользователей по активности
    """
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Общее количество
    total_query = select(func.count()).select_from(AuditLog).where(
        AuditLog.created_at >= date_from
    )
    result = await db.execute(total_query)
    total = result.scalar() or 0
    
    # По действиям
    action_query = (
        select(AuditLog.action, func.count())
        .where(AuditLog.created_at >= date_from)
        .group_by(AuditLog.action)
    )
    result = await db.execute(action_query)
    by_action = [{"action": row[0], "count": row[1]} for row in result.all()]
    
    # По типам ресурсов
    resource_query = (
        select(AuditLog.resource_type, func.count())
        .where(AuditLog.created_at >= date_from)
        .group_by(AuditLog.resource_type)
    )
    result = await db.execute(resource_query)
    by_resource = [{"resource_type": row[0], "count": row[1]} for row in result.all()]
    
    # Топ-10 пользователей
    user_query = (
        select(AuditLog.user_id, AuditLog.user_type, func.count())
        .where(AuditLog.created_at >= date_from)
        .group_by(AuditLog.user_id, AuditLog.user_type)
        .order_by(desc(func.count()))
        .limit(10)
    )
    result = await db.execute(user_query)
    top_users = [
        {
            "user_id": str(row[0]) if row[0] else None,
            "user_type": row[1],
            "count": row[2],
        }
        for row in result.all()
    ]
    
    return {
        "period_days": days,
        "date_from": date_from,
        "total_events": total,
        "by_action": by_action,
        "by_resource": by_resource,
        "top_users": top_users,
    }
