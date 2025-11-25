# db/init_celery.py
import asyncio
import logging
from .database import init_models

logger = logging.getLogger(__name__)

def initialize_celery_models():
    """Initialize models for Celery (synchronous wrapper)"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a task
            asyncio.create_task(init_models())
        else:
            # If no loop, run until complete
            loop.run_until_complete(init_models())
    except Exception as e:
        logger.error(f"Error initializing models in Celery: {e}")
