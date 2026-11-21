"""Password hashing, sign-in sessions and the dependencies routes use to require a signed-in user or role."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import User, UserSession

DEMO_EMAIL_DOMAIN = "@reprocare.demo"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


# Used when no account matches, so a wrong email takes as long to reject as a wrong password.
_DUMMY_HASH = bcrypt.hashpw(b"reprocare-timing-guard", bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (password_hash or _DUMMY_HASH).encode()) and password_hash is not None
    except ValueError:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    """Stage a session in the caller’s transaction and return its raw token."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.session_days)
    # Housekeeping: drop this user's expired sessions so the table does not grow forever.
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    db.add(UserSession(user_id=user.id, token_hash=_hash_token(token), expires_at=expires))
    return token


def end_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == _hash_token(token)))
    db.commit()


def end_other_sessions(db: Session, user: User, keep_token: str | None = None) -> int:
    """Sign the user out everywhere except (optionally) the current session. Returns sessions ended."""
    query = delete(UserSession).where(UserSession.user_id == user.id)
    if keep_token:
        query = query.where(UserSession.token_hash != _hash_token(keep_token))
    result = db.execute(query)
    db.commit()
    return result.rowcount or 0


def demo_accounts_blocked(email: str) -> bool:
    return email.lower().endswith(DEMO_EMAIL_DOMAIN) and (settings.is_production or not settings.allow_demo_accounts)


def _bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def get_optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    token = _bearer_token(authorization)
    if not token:
        return None
    row = db.scalar(select(UserSession).where(UserSession.token_hash == _hash_token(token)))
    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None
    user = db.get(User, row.user_id)
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.")
    return user


def get_session_token(authorization: str | None = Header(default=None)) -> str:
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.")
    return token


def require_role(*roles: str):
    """Dependency factory: `user = Depends(require_role("admin"))`."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account does not have access to this area.")
        return user

    return checker


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone or "",
        "role": user.role,
        "facility": {"id": user.facility.id, "slug": user.facility.slug, "name": user.facility.name}
        if user.facility
        else None,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
