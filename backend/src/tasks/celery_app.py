# celery_app.py
import os
from celery import Celery
from db.database import init_models
import asyncio

redis_password = os.getenv('REDIS_PASSWORD', '')

celery = Celery(
    'tasks',
    broker=f'redis://:{redis_password}@redis:6379/0',
    backend=f'redis://:{redis_password}@redis:6379/0'
)

# Инициализация моделей при запуске Celery
@celery.on_after_configure.connect
def setup_models(sender, **kwargs):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(init_models())
        else:
            loop.run_until_complete(init_models())
    except Exception as e:
        print(f"Models init in Celery: {e}")
