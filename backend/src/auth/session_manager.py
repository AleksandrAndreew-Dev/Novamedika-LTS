import uuid
import time
import json
import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.qa_models import Pharmacist, User
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

# Redis connection for session storage (production-ready)
_redis_client = None


def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv(
            "REDIS_URL", "redis://:your_redis_password_here@redis:6379/1"
        )
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def create_session_token(
    telegram_id: int, pharmacist_uuid: str, user_id: str
) -> str:
    """Create a simple session token and store in Redis"""
    token = str(uuid.uuid4())
    session_data = {
        "telegram_id": telegram_id,
        "pharmacist_uuid": pharmacist_uuid,
        "user_id": user_id,
        "created_at": time.time(),
        "expires_at": time.time() + 86400,  # 24 hours
    }

    # Store in Redis with expiration
    redis_client = get_redis_client()
    await redis_client.setex(
        f"session:{token}", 86400, json.dumps(session_data)  # TTL 24 hours
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
        logger.warning(f"Session not found in Redis for token {token[:10]}...")
        return None

    pharmacist_uuid = session.get("pharmacist_uuid")
    session_telegram_id = session.get("telegram_id")

    logger.info(
        f"Session found: pharmacist_uuid={pharmacist_uuid}, telegram_id={session_telegram_id}, "
        f"expires_at={session.get('expires_at')}"
    )

    result = await db.execute(
        select(Pharmacist)
        .options(selectinload(Pharmacist.user))
        .where(Pharmacist.uuid == pharmacist_uuid)
        .where(Pharmacist.is_active == True)
    )
    pharmacist = result.scalar_one_or_none()

    if not pharmacist:
        logger.warning(f"Pharmacist not found in DB for uuid={pharmacist_uuid}")
        return None

    # Access the actual attribute values (not Column objects)
    # Check both unencrypted and encrypted telegram_id
    pharmacist_telegram_id = getattr(pharmacist.user, "telegram_id", None)
    encrypted_id = getattr(pharmacist.user, "telegram_id_encrypted", None)

    logger.info(
        f"Pharmacist found: uuid={pharmacist.uuid}, "
        f"user_telegram_id={pharmacist_telegram_id}, "
        f"encrypted_id_present={bool(encrypted_id)}"
    )

    if pharmacist_telegram_id == session_telegram_id:
        logger.info(f"Telegram ID match (unencrypted) for pharmacist {pharmacist.uuid}")
        return pharmacist

    # Fallback: check encrypted telegram_id if direct field is null
    if pharmacist_telegram_id is None and encrypted_id:
        try:
            from utils.encryption import decrypt_bigint

            decrypted_id = decrypt_bigint(encrypted_id)
            logger.info(
                f"Encrypted telegram_id decrypted: {decrypted_id}, "
                f"session telegram_id: {session_telegram_id}"
            )
            if decrypted_id == session_telegram_id:
                # Sync back the unencrypted field for future lookups
                pharmacist.user.telegram_id = decrypted_id
                logger.info(
                    f"Telegram ID match (encrypted fallback) for pharmacist {pharmacist.uuid}"
                )
                return pharmacist
        except Exception as e:
            logger.error(f"Failed to decrypt telegram_id: {e}")

    logger.warning(
        f"Telegram ID mismatch: session={session_telegram_id}, "
        f"db_unencrypted={pharmacist_telegram_id}, "
        f"db_encrypted_present={bool(encrypted_id)}"
    )
    return None
