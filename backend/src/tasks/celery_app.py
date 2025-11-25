# celery_app.py
import os
from celery import Celery
from db.init_celery import initialize_celery_models

redis_password = os.getenv('REDIS_PASSWORD', '')

celery = Celery(
    'tasks',
    broker=f'redis://:{redis_password}@redis:6379/0',
    backend=f'redis://:{redis_password}@redis:6379/0'
)

# Initialize models when Celery starts
@celery.on_after_configure.connect
def setup_models(sender, **kwargs):
    initialize_celery_models()
