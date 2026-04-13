"""Модуль аутентификации для защиты эндпоинтов."""

import os
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader
import secrets
import logging

logger = logging.getLogger(__name__)

# --- HTTP Basic Auth (для админских эндпоинтов) ---
admin_security = HTTPBasic()


def get_admin_credentials(
    credentials: HTTPBasicCredentials = Depends(admin_security),
):
    """Защита через HTTP Basic — для критичных операций (удаление данных, загрузка)"""
    admin_user = os.getenv("ADMIN_USER")
    admin_pass = os.getenv("ADMIN_PASSWORD")

    if not admin_user or not admin_pass:
        logger.critical("ADMIN_USER/ADMIN_PASSWORD not configured — admin endpoints blocked")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin auth not configured",
        )

    is_user = secrets.compare_digest(credentials.username, admin_user)
    is_pass = secrets.compare_digest(credentials.password, admin_pass)

    if not (is_user and is_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin credentials",
            headers={"WWW-Authenticate": 'Basic realm="Admin"'},
        )

    return credentials.username


# --- API Key Auth (для booking orders и questions) ---
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


def get_api_key(api_key: str = Depends(api_key_header)):
    """Защита через API Key header — для booking и questions"""
    valid_keys_str = os.getenv("BOOKING_API_KEYS", "")
    valid_keys = [k.strip() for k in valid_keys_str.split(",") if k.strip()]

    if not valid_keys:
        logger.critical("BOOKING_API_KEYS not configured — booking/questions endpoints blocked")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key auth not configured",
        )

    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return api_key
