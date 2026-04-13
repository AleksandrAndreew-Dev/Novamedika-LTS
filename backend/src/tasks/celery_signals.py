"""
Celery signals — автоматический запуск задач при старте worker'а.
"""
from celery.signals import worker_ready
from celery import current_app
import logging

logger = logging.getLogger(__name__)


@worker_ready.connect
def at_worker_ready(sender, **kwargs):
    """
    Запускается один раз при старте celery worker'а.
    Запускает синхронизацию с tabletka.by немедленно (первый запуск).
    Далее задача выполняется по расписанию beat (каждые 8 часов).
    """
    logger.info("Worker ready — запуск первой синхронизации с tabletka.by")
    try:
        from tasks.tasks_increment import sync_tabletka_pharmacies_task
        sync_tabletka_pharmacies_task.delay()
        logger.info("Tabletka sync task queued successfully")
    except Exception as e:
        logger.error(f"Failed to queue tabletka sync task: {e}")
