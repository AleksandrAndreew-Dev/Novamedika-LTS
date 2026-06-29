import uuid
import time
import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.qa_models import Pharmacist
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

# Redis connection for session storage (production-ready)
_redis_client = None

# Helper key prefix for mapping telegram_id → current token
SESSION_MAP_PREFIX = "session_map:"
SESSION_PREFIX = "session:"
SESSION_TTL = 86400  # 24 hours


def _build_redis_url() -> str:
    """Build Redis URL from REDIS_URL or individual REDIS_* env vars"""
    url = os.getenv("REDIS_URL")
    if url:
        return url
    # Fallback: build from REDIS_HOST/PORT/DB/PASSWORD
    password = os.getenv("REDIS_PASSWORD", "")
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "1")
    if password:
        from urllib.parse import quote

        return f"redis://:{quote(password)}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        redis_url = _build_redis_url()
        logger.info(f"Connecting to Redis at: {redis_url.rsplit('@', 1)[-1]}")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def create_session_token(
    telegram_id: int, pharmacist_uuid: str, user_id: str
) -> str:
    """Create a session token and store in Redis.
    Atomically replaces any previous session for the same telegram_id."""
    token = str(uuid.uuid4())
    session_data = {
        "telegram_id": telegram_id,
        "pharmacist_uuid": pharmacist_uuid,
        "user_id": user_id,
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
    }

    redis_client = get_redis_client()

    # 1. Atomically invalidate previous session for this telegram_id
    map_key = f"{SESSION_MAP_PREFIX}{telegram_id}"
    old_token = await redis_client.get(map_key)
    if old_token:
        await redis_client.delete(f"{SESSION_PREFIX}{old_token}")
        logger.info(
            f"Invalidated stale session {old_token[:10]}... for telegram_id={telegram_id}"
        )

    # 2. Store new session atomically with the map key
    pipe = redis_client.pipeline()
    pipe.setex(f"{SESSION_PREFIX}{token}", SESSION_TTL, json.dumps(session_data))
    pipe.setex(map_key, SESSION_TTL, token)
    await pipe.execute()

    logger.info(f"Created session {token[:10]}... for telegram_id={telegram_id}")

    return token


async def get_session(token: str) -> Optional[dict]:
    """Get session data by token from Redis"""
    redis_client = get_redis_client()
    session_json = await redis_client.get(f"{SESSION_PREFIX}{token}")

    if not session_json:
        logger.warning(f"Session {token[:10]}... not found in Redis")
        return None

    try:
        session = json.loads(session_json)
        return session
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode session JSON for {token[:10]}...: {e}")
        return None


async def delete_session(token: str) -> bool:
    """Delete a session and its mapping from Redis"""
    redis_client = get_redis_client()
    session_json = await redis_client.get(f"{SESSION_PREFIX}{token}")
    if session_json:
        try:
            session = json.loads(session_json)
            telegram_id = session.get("telegram_id")
            if telegram_id:
                await redis_client.delete(f"{SESSION_MAP_PREFIX}{telegram_id}")
        except json.JSONDecodeError:
            pass
    result = await redis_client.delete(f"{SESSION_PREFIX}{token}")
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
        logger.warning(
            f"Pharmacist not found in DB for uuid={pharmacist_uuid}, session_telegram_id={session_telegram_id}"
        )
        return None

    # Verify telegram_id matches — critical auth check
    pharmacist_telegram_id = getattr(pharmacist.user, "telegram_id", None)
    encrypted_id = getattr(pharmacist.user, "telegram_id_encrypted", None)

    logger.info(
        f"Auth check: session_telegram_id={session_telegram_id}, "
        f"db_telegram_id={pharmacist_telegram_id}, "
        f"encrypted_present={bool(encrypted_id)}"
    )

    if (
        pharmacist_telegram_id is not None
        and pharmacist_telegram_id == session_telegram_id
    ):
        logger.info(f"Telegram ID match for pharmacist {pharmacist.uuid}")
        return pharmacist

    # Fallback: decrypt encrypted telegram_id
    if pharmacist_telegram_id is None and encrypted_id:
        try:
            from utils.encryption import decrypt_bigint

            decrypted_id = decrypt_bigint(encrypted_id)
            logger.info(
                f"Decrypted telegram_id={decrypted_id} matches session={session_telegram_id}"
            )
            if decrypted_id == session_telegram_id:
                # Cache decrypted value for next time
                pharmacist.user.telegram_id = decrypted_id
                logger.info(
                    f"Telegram ID match via decryption for pharmacist {pharmacist.uuid}"
                )
                return pharmacist
        except Exception as e:
            logger.error(f"Failed to decrypt telegram_id: {e}")

    logger.warning(
        f"Telegram ID mismatch — session={session_telegram_id}, "
        f"db_unencrypted={pharmacist_telegram_id}"
    )
    return None
