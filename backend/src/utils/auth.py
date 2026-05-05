"""
Shared authentication utilities for admin endpoints.
"""
import os
from typing import List
from fastapi import Header, HTTPException


def get_admin_api_keys() -> List[str]:
    """Получить список ADMIN API Keys из окружения"""
    keys_str = os.getenv("ADMIN_API_KEYS", "")
    return [k.strip() for k in keys_str.split(",") if k.strip()]


async def verify_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Проверка admin API key для защищенных endpoints.
    
    Требует header: X-API-Key с валидным ключом из ADMIN_API_KEYS env var.
    
    Raises:
        HTTPException: 401 если ключ неверный или не настроен
    """
    admin_keys = get_admin_api_keys()
    
    if not admin_keys:
        raise HTTPException(
            status_code=500,
            detail="Admin API keys not configured (set ADMIN_API_KEYS env var)",
        )
    
    if x_api_key not in admin_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin API key",
        )
    
    return True
