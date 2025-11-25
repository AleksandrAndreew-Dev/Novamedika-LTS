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

# Улучшенная инициализация моделей
@celery.on_after_configure.connect
def setup_models(sender, **kwargs):
    """Инициализация моделей при запуске Celery"""
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        from db.database import init_models

        # Создаем новую event loop для инициализации
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Запускаем инициализацию
        if loop.is_running():
            asyncio.create_task(init_models())
        else:
            loop.run_until_complete(init_models())

        logger.info("Database models initialized successfully in Celery")
    except Exception as e:
        logger.error(f"Error initializing models in Celery: {e}")
