# celery_app.py
import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Используем Redis как брокер и бэкенд (убираем RabbitMQ)
redis_password = os.getenv('REDIS_PASSWORD', '')
redis_host = os.getenv('REDIS_HOST', 'redis')

celery = Celery(
    'tasks',
    broker=f'redis://:{redis_password}@{redis_host}:6379/0',
    backend=f'redis://:{redis_password}@{redis_host}:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Важные настройки для решения проблем
celery.conf.update(
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_ignore_result=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
)
