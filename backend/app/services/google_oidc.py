"""Sign in with Google (OpenID Connect, authorization code flow with PKCE)."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlencode, urlsplit

import httpx
from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import GoogleAuthorization, GoogleIdentity, User, UserSession
from app.models.google_identity import GoogleLinkAuthorization
from app.schemas.google_auth import GoogleExchange, GoogleLinkStart, GoogleStart
from app.services import rate_limit
from app.services.auth_service import (
    DEMO_EMAIL_DOMAIN, _hash_token, create_session, hash_password, user_to_dict, verify_password,
)

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTHORIZATION_TTL = timedelta(minutes=10)
RESTART_MESSAGE = "This Google sign-in request could not be verified. Start again."
COLLISION_MESSAGE = "Use your existing sign-in method or contact ReproCare support."
LINK_UNAVAILABLE = "Connecting a Google account is currently unavailable."
LINK_CONFLICT = "A Google account is already connected. Contact ReproCare support for help."


@lru_cache(maxsize=1)
def _google_verifier():
    # the google-auth package is optional, without it Google sign-in stays off
    try:
        import requests
        from google.auth import exceptions
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
    except ImportError:
        return None
    return id_token, Request, requests, exceptions


def _redirect_configured() -> bool:
    # the redirect link must be https (http only allowed on localhost while developing)
    try:
        url = urlsplit(settings.google_oauth_redirect_uri)
        port = url.port
    except ValueError:
        return False
    if (
        not url.hostname or url.username is not None or url.password is not None
        or url.query or url.fragment or url.path != "/auth/google/callback"
        or any(ord(char) <= 32 or char == "\\" for char in settings.google_oauth_redirect_uri)
    ):
        return False
    if url.scheme == "https":
        return True
    return (
        url.scheme == "http" and not settings.is_production and port is not None
        and url.hostname in {"localhost", "127.0.0.1", "::1"}
    )


def enabled(db: Session) -> bool:
    if not (
        settings.google_oauth_enabled and settings.google_oauth_client_id
        and settings.google_oauth_client_secret and _redirect_configured() and _google_verifier()
    ):
        return False
    # the tables from migration 0005 must exist too
    schema = inspect(db.connection())
    return schema.has_table(GoogleIdentity.__tablename__) and schema.has_table(GoogleAuthorization.__tablename__)


def require_enabled(db: Session) -> None:
    if not enabled(db):
        raise HTTPException(503, "Google sign-in is currently unavailable.")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _challenge(verifier: str) -> str:
    hashed = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")


def _link_available(db: Session, user: User) -> bool:
    return (
        not user.email.lower().endswith(DEMO_EMAIL_DOMAIN) and enabled(db)
        and inspect(db.connection()).has_table(GoogleLinkAuthorization.__tablename__)
    )


def _linked(db: Session, user_id: int) -> bool:
    return db.scalar(select(GoogleIdentity.subject).where(GoogleIdentity.user_id == user_id)) is not None


def has_identity(db: Session, user: User) -> bool:
    """True when the account is linked to Google (needs migration 0005)."""
    if not inspect(db.get_bind()).has_table(GoogleIdentity.__tablename__):
        return False
    return _linked(db, user.id)


def link_status(db: Session, user: User) -> dict:
    available = _link_available(db, user)
    return {"available": available, "linked": available and _linked(db, user.id)}


def _link_binding(token: str, password_hash: str) -> str:
    # ties a link request to this session and this password
    return _digest(f"{_hash_token(token)}:{password_hash}")


def _begin(
    db: Session, challenge: str, intent: str, *, owner: User | None = None, token: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    # clear expired attempts first
    db.execute(delete(GoogleAuthorization).where(GoogleAuthorization.expires_at < now))
    state_hash = _digest(state)
    db.add(GoogleAuthorization(
        state_hash=state_hash, challenge=challenge, nonce=nonce,
        intent=intent, expires_at=now + AUTHORIZATION_TTL,
    ))
    if owner is not None and token is not None:
        db.flush()
        db.add(GoogleLinkAuthorization(
            state_hash=state_hash, user_id=owner.id, binding=_link_binding(token, owner.password_hash),
        ))
    db.commit()
    parameters = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "nonce": nonce,
    }
    if owner is not None:
        parameters["prompt"] = "select_account"
    return {"url": f"{AUTHORIZATION_URL}?{urlencode(parameters)}", "state": state}


def begin(db: Session, body: GoogleStart, client_address: str) -> dict:
    require_enabled(db)
    key = f"ip:google-start:{client_address}"
    rate_limit.check(key)
    rate_limit.record_failure(key)
    return _begin(db, body.challenge, body.intent)


def begin_link(db: Session, body: GoogleLinkStart, user: User, token: str, client_address: str) -> dict:
    if not _link_available(db, user):
        raise HTTPException(503, LINK_UNAVAILABLE)
    account_key = f"email:{user.email.lower()}"
    address_key = f"ip:google-link-start:{client_address}"
    rate_limit.check(account_key, address_key)
    rate_limit.record_failure(address_key)
    # must confirm the ReproCare password before linking Google
    if not verify_password(body.current_password, user.password_hash):
        rate_limit.record_failure(account_key)
        raise HTTPException(400, "Your ReproCare password is incorrect.")
    rate_limit.reset(account_key)
    if _linked(db, user.id):
        raise HTTPException(409, LINK_CONFLICT)
    return _begin(db, body.challenge, "link", owner=user, token=token)


def _verify_code(code: str, verifier: str) -> dict:
    id_token, auth_request, requests, exceptions = _google_verifier()
    try:
        # swap the one-time code for Google's id token
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
            response = client.post(TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            })
            response.raise_for_status()
            token = response.json().get("id_token")
        if not isinstance(token, str) or not token:
            raise ValueError
        with requests.Session() as session:
            session.trust_env = False
            google_request = auth_request(session=session)

            def fetch_certificate(url, method="GET", body=None, headers=None, **kwargs):
                return google_request(url, method=method, body=body, headers=headers, timeout=8)

            # google's library checks the signature, issuer, audience and expiry
            return id_token.verify_oauth2_token(token, fetch_certificate, settings.google_oauth_client_id)
    except (httpx.RequestError, exceptions.TransportError):
        raise HTTPException(503, "Google sign-in could not be reached. Try again shortly.") from None
    except (httpx.HTTPStatusError, ValueError, AttributeError, exceptions.GoogleAuthError):
        raise HTTPException(400, RESTART_MESSAGE) from None


def _consume(
    db: Session, body: GoogleExchange, *, owner: User | None = None, token: str | None = None,
) -> tuple[str, str, str | None]:
    # find the saved attempt, check it, then delete it so it can't be used twice
    attempt = db.scalar(
        select(GoogleAuthorization)
        .where(GoogleAuthorization.state_hash == _digest(body.state))
        .with_for_update()
    )
    if (
        attempt is None or attempt.expires_at <= datetime.now(timezone.utc)
        or not secrets.compare_digest(attempt.challenge, _challenge(body.verifier))
    ):
        raise HTTPException(400, RESTART_MESSAGE)
    binding = None
    if attempt.intent == "link":
        if owner is None or token is None:
            raise HTTPException(400, RESTART_MESSAGE)
        link = db.get(GoogleLinkAuthorization, attempt.state_hash)
        if (
            link is None or link.user_id != owner.id
            or not secrets.compare_digest(link.binding, _link_binding(token, owner.password_hash))
        ):
            raise HTTPException(400, RESTART_MESSAGE)
        binding = link.binding
    elif owner is not None:
        raise HTTPException(400, RESTART_MESSAGE)
    nonce, intent = attempt.nonce, attempt.intent
    db.delete(attempt)
    db.commit()
    return nonce, intent, binding


def _verified_claims(body: GoogleExchange, nonce: str) -> dict:
    claims = _verify_code(body.code, body.verifier)
    if claims.get("nonce") != nonce or claims.get("azp", settings.google_oauth_client_id) != settings.google_oauth_client_id:
        raise HTTPException(400, RESTART_MESSAGE)
    return claims


def _subject(claims: dict) -> str:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise HTTPException(400, RESTART_MESSAGE)
    return subject


def _account(db: Session, claims: dict, intent: str) -> User:
    subject = _subject(claims)
    identity = db.get(GoogleIdentity, subject)
    if identity is not None:
        user = db.get(User, identity.user_id)
        if user is None or not user.is_active or user.email.lower().endswith(DEMO_EMAIL_DOMAIN):
            raise HTTPException(403, COLLISION_MESSAGE)
        return user

    # only "register" makes a new patient, an existing email is never linked automatically
    if intent != "register":
        raise HTTPException(409, "No ReproCare account is linked to this Google account. Create an account or use your existing sign-in method.")
    email = _verified_email(claims)
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(409, COLLISION_MESSAGE)
    full_name = claims.get("name")
    full_name = full_name.strip()[:120] if isinstance(full_name, str) else ""
    user = User(email=email, full_name=full_name or "ReproCare patient", role="patient", password_hash=hash_password(secrets.token_urlsafe(40)))
    db.add(user)
    db.flush()
    db.add(GoogleIdentity(subject=subject, user_id=user.id))
    return user


def _verified_email(claims: dict) -> str:
    address = claims.get("email")
    if claims.get("email_verified") is not True or not isinstance(address, str):
        raise HTTPException(400, "Google did not provide a verified email address.")
    try:
        email = validate_email(address, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise HTTPException(400, "Google did not provide a usable email address.") from None
    if email.endswith(DEMO_EMAIL_DOMAIN):
        raise HTTPException(409, COLLISION_MESSAGE)
    # gmail, or a work account whose domain Google manages
    if not (email.endswith("@gmail.com") or isinstance(claims.get("hd"), str) and claims["hd"].strip()):
        raise HTTPException(409, "Use a Google account that manages and verifies this email address.")
    return email


def finish(db: Session, body: GoogleExchange, client_address: str) -> dict:
    require_enabled(db)
    key = f"ip:google-exchange:{client_address}"
    rate_limit.check(key)
    rate_limit.record_failure(key)
    nonce, intent, _ = _consume(db, body)
    claims = _verified_claims(body, nonce)
    try:
        user = _account(db, claims, intent)
        token = create_session(db, user)
        response = {"token": token, "user": user_to_dict(user)}
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, COLLISION_MESSAGE) from None
        raise
    return response


def finish_link(db: Session, body: GoogleExchange, user: User, token: str, client_address: str) -> None:
    if not _link_available(db, user):
        raise HTTPException(503, LINK_UNAVAILABLE)
    key = f"ip:google-link-exchange:{client_address}"
    rate_limit.check(key)
    rate_limit.record_failure(key)
    nonce, _, binding = _consume(db, body, owner=user, token=token)
    claims = _verified_claims(body, nonce)
    subject = _subject(claims)
    email = _verified_email(claims)

    # check the account again, the password or session may have changed while at Google
    current = db.get(User, user.id, with_for_update=True, populate_existing=True)
    if (
        binding is None or current is None or not current.is_active or current.email.lower().endswith(DEMO_EMAIL_DOMAIN)
        or not secrets.compare_digest(binding, _link_binding(token, current.password_hash))
    ):
        raise HTTPException(400, RESTART_MESSAGE)
    session_id = db.scalar(select(UserSession.id).where(
        UserSession.user_id == current.id,
        UserSession.token_hash == _hash_token(token),
        UserSession.expires_at > datetime.now(timezone.utc),
    ).with_for_update())
    if session_id is None:
        raise HTTPException(400, RESTART_MESSAGE)
    if current.email.lower() != email:
        raise HTTPException(409, "Choose the verified Google email on your ReproCare account.")
    if _linked(db, current.id) or db.get(GoogleIdentity, subject) is not None:
        raise HTTPException(409, LINK_CONFLICT)
    try:
        db.add(GoogleIdentity(subject=subject, user_id=current.id))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, LINK_CONFLICT) from None
        raise