import uuid
import time
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.qa_models import Pharmacist, User

# In-memory session storage (for simplicity - in production, use Redis or database)
_sessions: Dict[str, dict] = {}

def create_session_token(telegram_id: int, pharmacist_uuid: str, user_id: str) -> str:
    """Create a simple session token"""
    token = str(uuid.uuid4())
    _sessions[token] = {
        'telegram_id': telegram_id,
        'pharmacist_uuid': pharmacist_uuid,
        'user_id': user_id,
        'created_at': time.time(),
        'expires_at': time.time() + 86400  # 24 hours
    }
    return token

def get_session(token: str) -> Optional[dict]:
    """Get session data by token"""
    if token not in _sessions:
        return None
    
    session = _sessions[token]
    if time.time() > session['expires_at']:
        # Session expired, clean it up
        del _sessions[token]
        return None
    
    return session

def delete_session(token: str) -> bool:
    """Delete a session"""
    if token in _sessions:
        del _sessions[token]
        return True
    return False

async def get_pharmacist_by_session(token: str, db: AsyncSession):
    """Get pharmacist object from session token"""
    session = get_session(token)
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
