# celery_app.py
import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Используем Redis как брокер и бэкенд (убираем RabbitMQ)
redis_password = os.getenv("REDIS_PASSWORD", "")
redis_host = os.getenv("REDIS_HOST", "redis")

celery = Celery(
    "tasks",
    broker=f"redis://:{redis_password}@{redis_host}:6379/0",
    backend=f"redis://:{redis_password}@{redis_host}:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
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
    worker_max_tasks_per_child=100,
    worker_disable_rate_limits=False,
    task_always_eager=False,
    broker_pool_limit=10,
    result_backend_always_retry=True,
    beat_schedule_filename="celerybeat-schedule",
    beat_scheduler="celery.beat.PersistentScheduler",
    worker_max_memory_per_child=256000,
    # Периодические задачи
    beat_schedule={
        "sync-tabletka-pharmacies": {
            "task": "tasks.tasks_increment.sync_tabletka_pharmacies_task",
            "schedule": 28800,  # 8 часов = 3 раза в день
            "options": {"expires": 3600},
        },
    },
)

# КРИТИЧЕСКИ ВАЖНО: Импортируем все задачи для регистрации
from tasks import tasks_increment
from tasks import celery_worker_init

# Регистрируем задачи
celery.autodiscover_tasks(["tasks"])
