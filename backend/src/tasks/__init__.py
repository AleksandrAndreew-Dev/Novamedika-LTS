# tasks/__init__.py
from .celery_app import celery

# Импортируем все подмодули для регистрации задач
from . import tasks_increment
from . import celery_worker_init

__all__ = ['celery', 'tasks_increment', 'celery_worker_init']
