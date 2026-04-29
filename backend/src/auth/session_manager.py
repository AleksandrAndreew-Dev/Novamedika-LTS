import uuid
import time
import json
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.qa_models import Pharmacist, User
import redis.asyncio as redis
import os

# Redis connection for session storage (production-ready)
_redis_client = None

def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://:your_redis_password_here@redis:6379/1")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client

async def create_session_token(telegram_id: int, pharmacist_uuid: str, user_id: str) -> str:
    """Create a simple session token and store in Redis"""
    token = str(uuid.uuid4())
    session_data = {
        'telegram_id': telegram_id,
        'pharmacist_uuid': pharmacist_uuid,
        'user_id': user_id,
        'created_at': time.time(),
        'expires_at': time.time() + 86400  # 24 hours
    }
    
    # Store in Redis with expiration
    redis_client = get_redis_client()
    await redis_client.setex(
        f"session:{token}",
        86400,  # TTL 24 hours
        json.dumps(session_data)
    )
    
    return token

async def get_session(token: str) -> Optional[dict]:
    """Get session data by token from Redis"""
    redis_client = get_redis_client()
    session_json = await redis_client.get(f"session:{token}")
    
    if not session_json:
        return None
    
    try:
        session = json.loads(session_json)
        return session
    except json.JSONDecodeError:
        return None

async def delete_session(token: str) -> bool:
    """Delete a session from Redis"""
    redis_client = get_redis_client()
    result = await redis_client.delete(f"session:{token}")
    return result > 0

async def get_pharmacist_by_session(token: str, db: AsyncSession):
    """Get pharmacist object from session token"""
    session = await get_session(token)
    if not session:
        return None
    
    result = await db.execute(
        select(Pharmacist)
        .options(selectinload(Pharmacist.user))
        .where(Pharmacist.uuid == session['pharmacist_uuid'])
        .where(Pharmacist.is_active == True)
    )
    pharmacist = result.scalar_one_or_none()
    
    if pharmacist:
        # Access the actual attribute values (not Column objects)
        pharmacist_telegram_id = getattr(pharmacist.user, 'telegram_id', None)
        if pharmacist_telegram_id == session['telegram_id']:
            return pharmacist
    
    return None