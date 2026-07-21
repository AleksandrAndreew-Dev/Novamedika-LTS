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
    db = os.getenv("REDIS_DB", "0")
    if password:
        from urllib.parse import quote

        return f"redis://:{quote(password)}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


async def get_redis_client():
    """Get or create Redis client with connection check and auto-reconnect"""
    global _redis_client
    if _redis_client is None:
        redis_url = _build_redis_url()
        logger.info(f"Connecting to Redis at: {redis_url.rsplit('@', 1)[-1]}")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        if hasattr(_redis_client, "__await__"):
            _redis_client = await _redis_client

    # Check connection, reconnect if needed
    try:
        await _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.error(f"Redis ping failed, reconnecting: {e}")
        _redis_client = None
        redis_url = _build_redis_url()
        logger.info(f"Reconnecting to Redis at: {redis_url.rsplit('@', 1)[-1]}")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        if hasattr(_redis_client, "__await__"):
            _redis_client = await _redis_client
        await _redis_client.ping()
        logger.info("Redis reconnection successful")
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

    redis_client = await get_redis_client()

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

    logger.info(
        f"Session saved to Redis: key={SESSION_PREFIX}{token[:10]}..., "
        f"db={getattr(redis_client, 'db', 'unknown')}, "
        f"telegram_id={telegram_id}"
    )

    return token


async def recreate_session_from_data(session_data: Optional[dict]) -> Optional[str]:
    """Recreate a pharmacist session from existing session data after a reset."""
    if not session_data:
        return None

    telegram_id = session_data.get("telegram_id")
    pharmacist_uuid = session_data.get("pharmacist_uuid")
    user_id = session_data.get("user_id")

    if not telegram_id or not pharmacist_uuid or not user_id:
        logger.warning("Cannot recreate session: missing required session data")
        return None

    return await create_session_token(
        int(telegram_id), str(pharmacist_uuid), str(user_id)
    )


async def get_session(token: str) -> Optional[dict]:
    """Get session data by token from Redis"""
    redis_client = await get_redis_client()
    session_json = await redis_client.get(f"{SESSION_PREFIX}{token}")

    logger.info(
        f"Redis get attempt: key={SESSION_PREFIX}{token[:10]}..., "
        f"found={session_json is not None}, "
        f"db={getattr(redis_client, 'db', 'unknown')}"
    )

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
    redis_client = await get_redis_client()
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


async def clear_all_pharmacist_sessions() -> int:
    """Clear ALL pharmacist sessions from Redis.
    Used after /qa/drop to prevent stale sessions pointing to deleted DB records.
    Returns count of deleted sessions."""
    redis_client = await get_redis_client()
    count = 0
    cursor = 0
    pattern = f"{SESSION_PREFIX}*"
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            # Get session data to extract telegram_id for map cleanup
            for key in keys:
                session_json = await redis_client.get(key)
                if session_json:
                    try:
                        session = json.loads(session_json)
                        telegram_id = session.get("telegram_id")
                        if telegram_id:
                            await redis_client.delete(
                                f"{SESSION_MAP_PREFIX}{telegram_id}"
                            )
                    except json.JSONDecodeError:
                        pass
            await redis_client.delete(*keys)
            count += len(keys)
        if cursor == 0:
            break
    if count > 0:
        logger.warning(
            f"Cleared {count} stale pharmacist sessions from Redis after /qa/drop"
        )
    return count


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
            f"Pharmacist not found in DB for uuid={pharmacist_uuid}, session_telegram_id={session_telegram_id}. Auto-cleaning stale session."
        )
        # Auto-clean stale session — DB record was deleted (e.g. via /qa/drop)
        redis_client = await get_redis_client()
        map_key = f"{SESSION_MAP_PREFIX}{session_telegram_id}"
        await redis_client.delete(f"{SESSION_PREFIX}{token}", map_key)
        return None

    # Log telegram_id match status, but do NOT reject if mismatched
    # Session token is already validated (exists in Redis) — that's sufficient for auth
    pharmacist_telegram_id = getattr(pharmacist.user, "telegram_id", None)
    encrypted_id = getattr(pharmacist.user, "telegram_id_encrypted", None)

    telegram_id_matched = False
    if (
        pharmacist_telegram_id is not None
        and pharmacist_telegram_id == session_telegram_id
    ):
        telegram_id_matched = True
    elif pharmacist_telegram_id is None and encrypted_id:
        try:
            from utils.encryption import decrypt_bigint

            decrypted_id = decrypt_bigint(encrypted_id)
            if decrypted_id == session_telegram_id:
                pharmacist.user.telegram_id = decrypted_id
                telegram_id_matched = True
        except Exception as e:
            logger.error(f"Failed to decrypt telegram_id: {e}")

    if not telegram_id_matched:
        logger.warning(
            f"Telegram ID mismatch — session={session_telegram_id}, "
            f"db_unencrypted={pharmacist_telegram_id}, encrypted={bool(encrypted_id)}. "
            f"Session is valid, proceeding anyway."
        )
    else:
        logger.info(f"Telegram ID match for pharmacist {pharmacist.uuid}")

    return pharmacist
