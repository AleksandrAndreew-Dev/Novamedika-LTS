# celery_app.py
import os
from celery import Celery
import asyncio
import logging

logger = logging.getLogger(__name__)

redis_password = os.getenv('REDIS_PASSWORD', '')

celery = Celery(
    'tasks',
    broker=f'redis://:{redis_password}@redis:6379/0',
    backend=f'redis://:{redis_password}@redis:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

