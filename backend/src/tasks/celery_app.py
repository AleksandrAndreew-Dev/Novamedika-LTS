# celery_app.py
import os
from celery import Celery
from db.init_celery import initialize_celery_models

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

# Улучшенная инициализация моделей для Celery
@celery.on_after_configure.connect
def setup_models(sender, **kwargs):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            asyncio.create_task(initialize_celery_models_async())
        else:
            loop.run_until_complete(initialize_celery_models_async())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_celery_models_async())

async def initialize_celery_models_async():
    """Асинхронная инициализация моделей для Celery"""
    from db.database import init_models
    await init_models()
