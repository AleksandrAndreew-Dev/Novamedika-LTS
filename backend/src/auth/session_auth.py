from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from auth.session_manager import get_pharmacist_by_session
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def get_current_pharmacist_session(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current pharmacist using session token from Authorization header.
    Expects: Authorization: session <token>
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'session <token>'",
        )

    session_token = parts[1]
    logger.info(f"Pharmacist auth check for session token: {session_token[:10]}...")

    pharmacist = await get_pharmacist_by_session(session_token, db)

    if pharmacist is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    # Check if pharmacist is active
    if not getattr(pharmacist, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pharmacist account is deactivated",
        )

    return pharmacist
