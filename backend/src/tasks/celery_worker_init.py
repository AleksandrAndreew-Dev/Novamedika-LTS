# celery_worker_init.py
import asyncio
import logging
from celery.signals import worker_process_init, worker_process_shutdown

logger = logging.getLogger(__name__)

@worker_process_init.connect
def on_worker_init(**kwargs):
    """Инициализация worker процесса - сбрасываем соединения"""
    logger.info("Worker process initializing - resetting database connections")

    # Сбрасываем engine после fork
    from db.database import reset_engine
    reset_engine()

    # Инициализируем модели в этом процессе
    from tasks_increment import initialize_task_models
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_task_models())
        loop.close()
    except Exception as e:
        logger.error(f"Error in worker init: {e}")

@worker_process_shutdown.connect
def on_worker_shutdown(**kwargs):
    """Очистка при завершении worker"""
    logger.info("Worker process shutting down - disposing connections")

    from db.database import dispose_engine
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dispose_engine())
        loop.close()
    except Exception as e:
        logger.error(f"Error in worker shutdown: {e}")
