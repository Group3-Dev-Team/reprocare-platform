"""SCRUM-8 hardening: deactivation signs out, sign-up limit, literal admin search, demo domain, expired-session cleanup."""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.database import cleanup_sessions
from app.database.session import SessionLocal
from app.models import User, UserSession
from app.services import rate_limit
from app.services.auth_service import _hash_token, purge_expired_sessions

PASSWORD = "HardeningTest1"


@pytest.fixture()
def fresh_limits(monkeypatch):
    # each test starts with empty rate-limit counters and leaves the shared ones as they were
    monkeypatch.setattr(rate_limit, "_attempts", defaultdict(deque))
    return monkeypatch


def _register(client, email):
    return client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Hardening Test"})


def _sessions(user_id):
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id))


# --- 1. Deactivation signs the account out everywhere ----------------------------------------------


def test_deactivation_ends_every_session_and_reactivation_does_not_revive_them(client, make_user):
    admin = make_user(role="admin")[1]
    other_user, other_headers = make_user()
    user, first = make_user(password=PASSWORD)
    second = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'email': user.email, 'password': PASSWORD}).json()['token']}"}
    assert _sessions(user.id) == 2

    response = client.patch(f"/api/admin/users/{user.id}", headers=admin, json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert _sessions(user.id) == 0
    assert client.get("/api/auth/me", headers=first).status_code == 401

    assert client.patch(f"/api/admin/users/{user.id}", headers=admin, json={"is_active": True}).json()["is_active"] is True
    assert client.get("/api/auth/me", headers=first).status_code == 401
    assert client.get("/api/auth/me", headers=second).status_code == 401
    # the reactivated person signs in again normally
    assert client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 200
    # nobody else was signed out, including the administrator
    assert client.get("/api/auth/me", headers=other_headers).json()["id"] == other_user.id
    assert client.get("/api/auth/me", headers=admin).status_code == 200


def test_activating_an_active_account_keeps_its_sessions(client, make_user):
    admin = make_user(role="admin")[1]
    user, headers = make_user()
    assert client.patch(f"/api/admin/users/{user.id}", headers=admin, json={"is_active": True}).status_code == 200
    assert client.get("/api/auth/me", headers=headers).json()["id"] == user.id


def test_admin_still_cannot_deactivate_themselves(client, make_user):
    admin, headers = make_user(role="admin")
    assert client.patch(f"/api/admin/users/{admin.id}", headers=headers, json={"is_active": False}).status_code == 400
    assert client.get("/api/auth/me", headers=headers).status_code == 200


# --- 2. Sign-up attempts are limited per network address ---------------------------------------------


def test_registration_uses_the_shared_address_limit():
    assert rate_limit._limit("ip:register:203.0.113.7") == rate_limit.MAX_FAILURES_PER_ADDRESS == 40


def test_registration_is_limited_per_address(client, fresh_limits, make_user):
    fresh_limits.setattr(rate_limit, "MAX_FAILURES_PER_ADDRESS", 3)  # the real limit is 40; 3 keeps the test fast
    assert _register(client, "limit-one@example.com").status_code == 201
    assert _register(client, "limit-one@example.com").status_code == 409  # duplicates count too
    assert _register(client, "limit-two@example.com").status_code == 201

    blocked = _register(client, "limit-three@example.com")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many sign-up attempts from this network. Please wait 15 minutes and try again."
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.email == "limit-three@example.com")) is None

    # signing in is limited separately, so existing users are not locked out
    assert client.post("/api/auth/login", json={"email": "limit-one@example.com", "password": PASSWORD}).status_code == 200
    user, _ = make_user(password=PASSWORD)
    assert client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 200


def test_registration_limit_expires(client, fresh_limits):
    fresh_limits.setattr(rate_limit, "MAX_FAILURES_PER_ADDRESS", 1)
    assert _register(client, "window-one@example.com").status_code == 201
    assert _register(client, "window-two@example.com").status_code == 429
    clock = rate_limit.time.monotonic() + rate_limit.WINDOW_SECONDS + 1
    fresh_limits.setattr(rate_limit.time, "monotonic", lambda: clock)
    assert _register(client, "window-two@example.com").status_code == 201


def test_invalid_sign_up_forms_are_rejected_before_counting(client, fresh_limits):
    fresh_limits.setattr(rate_limit, "MAX_FAILURES_PER_ADDRESS", 1)
    assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "x", "full_name": "A"}).status_code == 422
    assert _register(client, "after-invalid@example.com").status_code == 201


# --- 3. Admin user search treats % and _ literally -------------------------------------------------


def test_admin_user_search_is_literal(client, make_user):
    admin = make_user(role="admin")[1]
    percent, _ = make_user(full_name="Wanjiru 100% Verified")
    underscore, _ = make_user(email="first_last.search@example.com")

    def found(q):
        return {u["id"] for u in client.get("/api/admin/users", params={"q": q}, headers=admin).json()["items"]}

    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(User))
    assert len(found("%")) < total  # no longer matches everyone
    assert percent.id in found("100%") and percent.id in found("%")
    assert underscore.id in found("first_last") and underscore.id not in found("firstxlast")
    assert all("_" in (u["email"] + u["full_name"]) for u in client.get("/api/admin/users", params={"q": "_"}, headers=admin).json()["items"])
    # ordinary searches still match part of a name or email, ignoring case
    assert percent.id in found("WANJIRU") and underscore.id in found("LAST.SEARCH@")


# --- 4. Staff accounts cannot use the demonstration domain -----------------------------------------


@pytest.mark.parametrize("email", ["helper@reprocare.demo", "Helper@RePROcare.DEMO"])
@pytest.mark.parametrize("role", ["facility_staff", "admin"])
def test_staff_accounts_cannot_use_the_demo_domain(client, make_user, make_facility, email, role):
    admin = make_user(role="admin")[1]
    facility = make_facility()
    response = client.post(
        "/api/admin/users",
        headers=admin,
        json={"full_name": "Demo Helper", "email": email, "password": PASSWORD, "role": role, "facility_slug": facility.slug},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "This email domain is reserved for demonstration accounts."
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(func.lower(User.email) == email.lower())) is None


# --- 5. Expired sessions can be cleaned up ----------------------------------------------------------


def _add_session(user_id, token, expires_in):
    with SessionLocal() as db:
        db.add(UserSession(user_id=user_id, token_hash=_hash_token(token), expires_at=datetime.now(timezone.utc) + expires_in))
        db.commit()


def _token_exists(token):
    with SessionLocal() as db:
        return db.scalar(select(UserSession.id).where(UserSession.token_hash == _hash_token(token))) is not None


def test_cleanup_deletes_only_expired_sessions(client, make_user):
    first, first_headers = make_user()
    second, _ = make_user()
    _add_session(first.id, "cleanup-expired-a", timedelta(days=-3))
    _add_session(second.id, "cleanup-expired-b", timedelta(seconds=-1))
    _add_session(second.id, "cleanup-active", timedelta(minutes=5))

    with SessionLocal() as db:
        assert purge_expired_sessions(db, dry_run=True) >= 2
    assert _token_exists("cleanup-expired-a")  # a dry run changes nothing

    with SessionLocal() as db:
        assert purge_expired_sessions(db) >= 2
        assert purge_expired_sessions(db) == 0  # running it again is harmless
    assert not _token_exists("cleanup-expired-a") and not _token_exists("cleanup-expired-b")
    assert _token_exists("cleanup-active")
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer cleanup-active"}).json()["id"] == second.id
    assert client.get("/api/auth/me", headers=first_headers).json()["id"] == first.id
    with SessionLocal() as db:
        assert db.get(User, first.id).is_active and db.get(User, second.id).is_active  # only session rows are removed


def test_cleanup_command(make_user, capsys):
    user, _ = make_user()
    _add_session(user.id, "command-expired", timedelta(hours=-1))

    cleanup_sessions.main(["--dry-run"])
    assert "would be deleted (dry run, nothing changed)" in capsys.readouterr().out
    assert _token_exists("command-expired")

    cleanup_sessions.main([])
    assert capsys.readouterr().out.startswith("Deleted ")
    assert not _token_exists("command-expired")
    assert _sessions(user.id) == 1  # the active session from make_user is kept
