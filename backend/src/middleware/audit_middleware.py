"""
Middleware для автоматического аудита доступа к персональным данным.
Соответствует требованиям ОАЦ п.2.1 и Закону №99-З.
"""
import json
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from db.database import get_async_sessionmaker
from db.models import AuditLog
import uuid

logger = logging.getLogger(__name__)

# Endpoints, требующие аудита (доступ к персональным данным)
AUDITED_ENDPOINTS = [
    "/api/users",
    "/api/pharmacist",
    "/api/orders",
    "/api/questions",
    "/api/privacy",
]


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех запросов к endpoints с персональными данными.
    
    Записывает в БД:
    - Кто выполнил действие (user_id, user_type)
    - Какое действие (action, endpoint)
    - К каким данным обращались (resource_type, resource_id)
    - Технические детали (ip, user_agent, status_code)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Проверяем, нужно ли логировать этот endpoint
        path = request.url.path
        if not self._should_audit(path):
            return await call_next(request)

        # Извлекаем информацию о запросе
        start_time = datetime.utcnow()
        user_id = getattr(request.state, "user_id", None)
        user_type = getattr(request.state, "user_type", "anonymous")
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        
        # Определяем тип действия
        action = self._get_action_from_method(method)
        
        # Определяем тип ресурса из пути
        resource_type = self._get_resource_type(path)
        
        # Пытаемся извлечь resource_id из пути
        resource_id = self._extract_resource_id(path)

        try:
            # Выполняем запрос
            response = await call_next(request)
            
            # Логируем после выполнения
            await self._log_audit_event(
                user_id=user_id,
                user_type=user_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=method,
                endpoint=path,
                status_code=str(response.status_code),
                success=response.status_code < 400,
            )
            
            return response
            
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Audit middleware error: {str(e)}", exc_info=True)
            
            # Всё равно пытаемся залогировать событие (с ошибкой)
            try:
                await self._log_audit_event(
                    user_id=user_id,
                    user_type=user_type,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=method,
                    endpoint=path,
                    status_code="500",
                    success=False,
                    details={"error": str(e)},
                )
            except Exception:
                pass
            
            raise

    def _should_audit(self, path: str) -> bool:
        """Проверяет, нужно ли логировать данный endpoint"""
        return any(path.startswith(endpoint) for endpoint in AUDITED_ENDPOINTS)

    def _get_action_from_method(self, method: str) -> str:
        """Определяет тип действия по HTTP методу"""
        actions = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        return actions.get(method, "unknown")

    def _get_resource_type(self, path: str) -> str:
        """Определяет тип ресурса из пути"""
        if "/users" in path:
            return "user"
        elif "/pharmacist" in path:
            return "pharmacist"
        elif "/orders" in path:
            return "order"
        elif "/questions" in path:
            return "question"
        elif "/privacy" in path:
            return "consent"
        return "unknown"

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Пытается извлечь ID ресурса из пути"""
        parts = path.strip("/").split("/")
        # Ищем UUID в пути (обычно это последний или предпоследний элемент)
        for part in reversed(parts):
            try:
                uuid.UUID(part)
                return part
            except ValueError:
                continue
        return None

    async def _log_audit_event(
        self,
        user_id: Optional[str] = None,
        user_type: str = "anonymous",
        action: str = "unknown",
        resource_type: str = "unknown",
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
        request_method: str = "GET",
        endpoint: str = "",
        status_code: str = "200",
        success: bool = True,
        details: Optional[dict] = None,
    ):
        """Записывает событие аудита в БД"""
        try:
            sessionmaker = get_async_sessionmaker()
            async with sessionmaker() as db:
                audit_log = AuditLog(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    user_type=user_type,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent[:500],  # Ограничиваем длину
                    request_method=request_method,
                    endpoint=endpoint[:255],  # Ограничиваем длину
                    status_code=status_code,
                    success=success,
                    details=details,
                    created_at=datetime.utcnow(),
                )
                
                db.add(audit_log)
                await db.commit()
                
                logger.debug(
                    f"Audit log created: {user_type} {action} {resource_type} "
                    f"(status={status_code}, success={success})"
                )
                
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
            # Не прерываем основной поток из-за ошибки логирования
