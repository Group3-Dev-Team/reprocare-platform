"""Forgot password: make a reset link, email it, and use it to set a new password."""

import hashlib
import logging
import os
import secrets
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.password_reset import PasswordReset
from app.models.user import User, UserSession
from app.services.auth_service import DEMO_EMAIL_DOMAIN, hash_password

RESET_LIFETIME = timedelta(minutes=30)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryConfig:
    frontend_origin: str
    smtp_host: str
    smtp_port: int
    smtp_security: str
    smtp_from: str
    # repr=False so the email login is never printed in logs
    smtp_user: str = field(repr=False)
    smtp_password: str = field(repr=False)


def recovery_config() -> RecoveryConfig | None:
    # returns None (reset turned off) unless every email setting in .env is filled in correctly
    if os.getenv("PASSWORD_RESET_ENABLED", "").strip().lower() not in {"true", "1", "yes", "on"}:
        return None

    origin = os.getenv("PASSWORD_RESET_FRONTEND_ORIGIN", "").strip()
    host = os.getenv("PASSWORD_RESET_SMTP_HOST", "").strip()
    user = os.getenv("PASSWORD_RESET_SMTP_USER", "").strip()
    password = os.getenv("PASSWORD_RESET_SMTP_PASSWORD", "")
    security = os.getenv("PASSWORD_RESET_SMTP_SECURITY", "starttls").strip().lower()

    try:
        url = urlsplit(origin)
        _ = url.port  # reading the port checks it is a valid number
        sender = validate_email(os.getenv("PASSWORD_RESET_SMTP_FROM", ""), check_deliverability=False).normalized
        port = int(os.getenv("PASSWORD_RESET_SMTP_PORT", "587"))
    except (ValueError, EmailNotValidError):
        return None

    # plain http is only allowed for localhost while developing
    loopback_http = (
        url.scheme == "http"
        and settings.environment in {"development", "test"}
        and url.hostname in {"localhost", "127.0.0.1", "::1"}
    )
    if (
        not url.hostname or url.username is not None or url.password is not None
        or url.query or url.fragment or url.path not in {"", "/"}
        or any(char.isspace() or ord(char) < 32 or char == chr(92) for char in origin)
        or not (url.scheme == "https" or loopback_http)
        or not (host and user and password and 1 <= port <= 65535)
        or any(char.isspace() for char in host)
        or security not in {"starttls", "implicit-tls"}
    ):
        return None

    return RecoveryConfig(origin.rstrip("/"), host, port, security, sender, user, password)


def recovery_available(db: Session, config: RecoveryConfig | None) -> bool:
    # reset works only if email is set up and the password_resets table exists
    return config is not None and inspect(db.connection()).has_table(PasswordReset.__tablename__)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def send_reset_email(config: RecoveryConfig, recipient: str, link: str) -> None:
    message = EmailMessage()
    message["From"] = config.smtp_from
    message["To"] = recipient
    message["Subject"] = "Reset your ReproCare password"
    message.set_content(
        f"You requested a ReproCare password reset. Open this link within 30 minutes:\n\n{link}\n\n"
        "If you did not request a reset, you can ignore this email. Your password will stay the same."
    )
    context = ssl.create_default_context()
    if config.smtp_security == "implicit-tls":
        smtp = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=8, context=context)
    else:
        smtp = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=8)
    with smtp:
        if config.smtp_security == "starttls":
            smtp.starttls(context=context)
        smtp.login(config.smtp_user, config.smtp_password)
        smtp.send_message(message)


def queue_reset_email(config: RecoveryConfig, email: str) -> None:
    """Runs after the reply is sent, so the reply looks the same whether the account exists or not."""
    try:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(func.lower(User.email) == email).with_for_update())
            if user is None or not user.is_active or user.email.lower().endswith(DEMO_EMAIL_DOMAIN):
                return
            now = datetime.now(timezone.utc)
            token = secrets.token_urlsafe(32)
            # clean up old expired links first
            db.execute(delete(PasswordReset).where(PasswordReset.expires_at <= now))
            db.add(PasswordReset(
                token_hash=digest(token),
                user_id=user.id,
                password_fingerprint=digest(user.password_hash),
                expires_at=now + RESET_LIFETIME,
            ))
            recipient = user.email
            db.commit()

        # token goes after # so it is not sent to the server or leaked in referrers
        send_reset_email(config, recipient, f"{config.frontend_origin}/reset-password#token={token}")
    except (SQLAlchemyError, OSError, ValueError):
        # don't log the error itself, it can contain emails or the link
        logger.warning("Password recovery request could not be processed.")


def change_password_with_reset(db: Session, token: str, new_password: str) -> bool:
    token_hash = digest(token)
    user_id = db.scalar(select(PasswordReset.user_id).where(PasswordReset.token_hash == token_hash))
    if user_id is None:
        return False

    # lock the user row first so two resets at the same time can't both work
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    reset = db.get(PasswordReset, token_hash)
    if (
        user is None or not user.is_active or user.email.lower().endswith(DEMO_EMAIL_DOMAIN)
        or reset is None or reset.expires_at <= datetime.now(timezone.utc)
        or not secrets.compare_digest(reset.password_fingerprint, digest(user.password_hash))
    ):
        return False

    user.password_hash = hash_password(new_password)
    # one use only: remove all links and sign the user out everywhere
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    return True