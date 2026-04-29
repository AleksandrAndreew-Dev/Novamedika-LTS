from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from auth.session_manager import get_pharmacist_by_session

security = HTTPBearer()

async def get_current_pharmacist_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current pharmacist using session token instead of JWT
    """
    session_token = credentials.credentials
    
    pharmacist = await get_pharmacist_by_session(session_token, db)
    
    if pharmacist is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    # Check if pharmacist is active (handle SQLAlchemy column properly)
    if not getattr(pharmacist, 'is_active', False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pharmacist account is deactivated"
        )
    
    return pharmacist