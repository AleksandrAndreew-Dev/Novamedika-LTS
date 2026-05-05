"""
Middleware package для Novamedika2 backend.

Содержит middleware для:
- Аудита доступа к персональным данным
- Rate limiting (в разработке)
- Request ID generation (в разработке)
"""

from .audit_middleware import AuditLoggingMiddleware

__all__ = ["AuditLoggingMiddleware"]
