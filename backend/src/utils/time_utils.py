# utils/time_utils.py
from datetime import datetime, timezone

def get_utc_now():
    """Получение текущего времени в UTC с правильным timezone"""
    return datetime.now(timezone.utc)

def get_utc_now_naive():
    """Получение текущего времени в UTC без timezone (для совместимости)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
