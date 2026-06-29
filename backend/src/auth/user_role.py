"""Combined dependency for user+pharmacist role detection in REST API.

Works like RoleMiddleware from Telegram bot but for FastAPI:
- Injects user, pharmacist, is_pharmacist into endpoints
- Supports JWT (user), JWT (pharmacist), TMA (Telegram Mini App), API key (anonymous)
"""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
import logging
import uuid

from db.database import get_db
from db.qa_models import User, Pharmacist
from auth.auth import SECRET_KEY, ALGORITHM
import jwt
from jwt import InvalidTokenError, ExpiredSignatureError

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class CurrentUserRole:
    """Combined role context — similar to what RoleMiddleware injects in Telegram"""

    def __init__(
        self,
        user: Optional[User] = None,
        pharmacist: Optional[Pharmacist] = None,
        is_pharmacist: bool = False,
        is_anonymous: bool = False,
        auth_type: str = "none",
    ):
        self.user = user
        self.pharmacist = pharmacist
        self.is_pharmacist = is_pharmacist
        self.is_anonymous = is_anonymous
        self.auth_type = auth_type  # jwt_user, jwt_pharmacist, tma, api_key, session

    @property
    def user_id(self) -> Optional[str]:
        if self.user:
            return str(self.user.uuid)
        return None

    @property
    def pharmacist_id(self) -> Optional[str]:
        if self.pharmacist:
            return str(self.pharmacist.uuid)
        return None

    @property
    def effective_id(self) -> Optional[str]:
        """Get the effective user/entity ID — for filtering questions"""
        if self.is_pharmacist and self.pharmacist:
            return str(self.pharmacist.uuid)
        if self.user:
            return str(self.user.uuid)
        return None


async def get_tma_user(
    authorization: str,
    db: AsyncSession,
) -> Optional[User]:
    """Resolve user from Telegram Mini App initData"""
    if not authorization or not authorization.startswith("tma "):
        return None

    init_data = authorization[4:].strip()
    if not init_data:
        return None

    try:
        # Parse initData to extract user ID
        # Expected format: query_id=xxx&user=xxx&auth_date=xxx&hash=xxx
        from urllib.parse import parse_qs

        parsed = parse_qs(init_data)
        user_json = parsed.get("user", [None])[0]
        if not user_json:
            return None

        import json

        user_data = json.loads(user_json)
        telegram_id = user_data.get("id")
        if not telegram_id:
            return None

        # Find existing user by telegram_id
        from services.user_service import get_or_create_user

        return await get_or_create_user(db, telegram_id=telegram_id)

    except Exception as e:
        logger.warning(f"TMA auth parsing failed: {e}")
        return None


async def get_pharmacist_from_user(
    user: User,
    db: AsyncSession,
) -> Optional[Pharmacist]:
    """Find pharmacist linked to this user"""
    try:
        if not user.telegram_id:
            return None

        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.uuid)
            .options(selectinload(Pharmacist.user))
            .where(User.telegram_id == user.telegram_id)
            .where(Pharmacist.is_active == True)
        )
        return result.scalars().one_or_none()
    except Exception as e:
        logger.warning(f"Error finding pharmacist for user: {e}")
        return None


async def get_current_user_with_role(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    db: AsyncSession = Depends(get_db),
) -> CurrentUserRole:
    """
    Unified role detection dependency.

    Resolution order:
    1. JWT token (pharmacist) — if 'sub' matches a pharmacist UUID
    2. JWT token (user) — if 'sub' matches a user UUID
    3. TMA initData — from Telegram Mini App
    4. Session token — pharmacist session
    5. X-API-KEY — for anonymous/internal requests
    6. None — unauthenticated
    """
    # Case 1: No credentials at all
    if not credentials and not x_api_key:
        return CurrentUserRole(auth_type="none")

    # Case 2: API key — anonymous user
    if x_api_key:
        # X-API-KEY auth — used for anonymous public questions
        return CurrentUserRole(is_anonymous=True, auth_type="api_key")

    if not credentials:
        return CurrentUserRole(auth_type="none")

    token = credentials.credentials

    # Case 3: JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") == "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Try pharmacist first (JWT for pharmacist has 'sub' = pharmacist.uuid)
        ph_result = await db.execute(
            select(Pharmacist)
            .options(selectinload(Pharmacist.user))
            .where(Pharmacist.uuid == uuid.UUID(subject))
        )
        pharmacist = ph_result.scalars().one_or_none()
        if pharmacist and getattr(pharmacist, "is_active", False):
            user = pharmacist.user
            return CurrentUserRole(
                user=user,
                pharmacist=pharmacist,
                is_pharmacist=True,
                auth_type="jwt_pharmacist",
            )

        # Try user
        user_result = await db.execute(
            select(User).where(User.uuid == uuid.UUID(subject))
        )
        user = user_result.scalar_one_or_none()
        if user:
            # Check if user is also a pharmacist (linked via telegram_id)
            pharmacist = await get_pharmacist_from_user(user, db)
            return CurrentUserRole(
                user=user,
                pharmacist=pharmacist,
                is_pharmacist=pharmacist is not None,
                auth_type="jwt_user",
            )

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        # Not a valid JWT — try other auth methods
        pass
    except ValueError:
        pass
    except Exception as e:
        logger.warning(f"JWT auth error: {e}")

    # Case 4: TMA initData
    user = await get_tma_user(f"tma {token}", db)
    if user:
        pharmacist = await get_pharmacist_from_user(user, db)
        return CurrentUserRole(
            user=user,
            pharmacist=pharmacist,
            is_pharmacist=pharmacist is not None,
            auth_type="tma",
        )

    # Case 5: Session token (pharmacist dashboard)
    try:
        from auth.session_manager import get_pharmacist_by_session

        pharmacist = await get_pharmacist_by_session(token, db)
        if pharmacist and getattr(pharmacist, "is_active", False):
            user = pharmacist.user
            return CurrentUserRole(
                user=user,
                pharmacist=pharmacist,
                is_pharmacist=True,
                auth_type="session",
            )
    except Exception as e:
        logger.warning(f"Session auth failed: {e}")

    # Case 6: Token exists but no method resolved it
    return CurrentUserRole(auth_type="none")
