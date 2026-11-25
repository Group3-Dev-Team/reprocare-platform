"""Forgot password tests. Email sending is faked so nothing real is sent."""

from collections import defaultdict, deque
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from app.database.session import SessionLocal
from app.models.password_reset import PasswordReset
from app.services import password_recovery, rate_limit

PREFIX = "/api/auth/recovery"
NEW_PASSWORD = "Another123!"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    # never use a real mail server, even if one is set in .env
    monkeypatch.setenv("PASSWORD_RESET_ENABLED", "false")
    monkeypatch.setattr(rate_limit, "_attempts", defaultdict(deque))


@pytest.fixture
def recovery(monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_ENABLED", "true")
    monkeypatch.setenv("PASSWORD_RESET_FRONTEND_ORIGIN", "https://reprocare.example.com")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_PORT", "587")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_SECURITY", "starttls")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_FROM", "support@example.com")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_USER", "mock-mailer")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_PASSWORD", "mock-value")
    sent = []
    # save the emails in a list instead of sending them
    monkeypatch.setattr(password_recovery, "send_reset_email", lambda _, recipient, link: sent.append((recipient, link)))
    return sent


def request_link(client, email):
    return client.post(f"{PREFIX}/request", json={"email": email})


def reset_token(link):
    url = urlsplit(link)
    assert url.scheme == "https"
    assert url.hostname == "reprocare.example.com"
    assert url.path == "/reset-password"
    assert not url.query
    return parse_qs(url.fragment)["token"][0]


def test_disabled_recovery_does_not_accept_requests(client):
    assert client.get(f"{PREFIX}/status").json() == {"available": False}
    assert request_link(client, "unknown@example.com").status_code == 503


@pytest.mark.parametrize("origin", ["http://reprocare.example.com", "https://reprocare.example.com/another-page",
                                    "https://username@reprocare.example.com", "https://reprocare.example.com/?other=true"])
def test_invalid_frontend_origin_disables_recovery(client, recovery, monkeypatch, origin):
    monkeypatch.setenv("PASSWORD_RESET_FRONTEND_ORIGIN", origin)
    assert client.get(f"{PREFIX}/status").json() == {"available": False}
    assert request_link(client, "unknown@example.com").status_code == 503
    assert not recovery


def test_requests_are_neutral_and_send_only_for_eligible_accounts(client, make_user, recovery):
    user, _ = make_user()
    status = client.get(f"{PREFIX}/status")
    assert status.json() == {"available": True}
    assert status.headers["Cache-Control"] == "no-store"

    known = request_link(client, user.email)
    unknown = request_link(client, "no-reset-user@example.com")
    reserved = request_link(client, "staff@reprocare.demo")
    # same reply for all three, but only the real account gets an email
    assert known.status_code == unknown.status_code == reserved.status_code == 202
    assert known.json() == unknown.json() == reserved.json()
    assert [recipient for recipient, _ in recovery] == [user.email]
    assert reset_token(recovery[0][1]) not in known.text


def test_success_revokes_active_sessions_and_all_reset_links(client, make_user, recovery):
    user, first_session = make_user()
    other = client.post("/api/auth/login", json={"email": user.email, "password": "Secret123"})
    assert other.status_code == 200
    second_session = {"Authorization": "Bearer " + other.json()["token"]}

    assert request_link(client, user.email).status_code == 202
    assert request_link(client, user.email).status_code == 202
    older_token = reset_token(recovery[0][1])
    token = reset_token(recovery[1][1])
    with SessionLocal() as db:
        # only the hash is saved, never the token itself
        assert db.get(PasswordReset, token) is None
        assert db.get(PasswordReset, password_recovery.digest(token)).user_id == user.id

    response = client.post(f"{PREFIX}/reset", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 204
    for session in (first_session, second_session):
        assert client.get("/api/auth/me", headers=session).status_code == 401
    for used in (token, older_token):
        assert client.post(f"{PREFIX}/reset", json={"token": used, "new_password": "Other1234"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": user.email, "password": "Secret123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": user.email, "password": NEW_PASSWORD}).status_code == 200


def test_expired_link_does_not_change_password(client, make_user, recovery, monkeypatch):
    user, session = make_user()
    monkeypatch.setattr(password_recovery, "RESET_LIFETIME", timedelta(seconds=-1))
    assert request_link(client, user.email).status_code == 202
    response = client.post(f"{PREFIX}/reset", json={"token": reset_token(recovery[0][1]), "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert client.get("/api/auth/me", headers=session).status_code == 200


def test_regular_password_change_invalidates_earlier_recovery_link(client, make_user, recovery):
    user, session = make_user()
    assert request_link(client, user.email).status_code == 202
    assert client.post("/api/auth/change-password", headers=session, json={
        "current_password": "Secret123", "new_password": "Change123!"
    }).status_code == 204
    response = client.post(f"{PREFIX}/reset", json={"token": reset_token(recovery[0][1]), "new_password": NEW_PASSWORD})
    assert response.status_code == 400


def test_validation_does_not_echo_secrets(client, recovery):
    token = "should-never-be-returned"
    password = "Aa1" + "x" * 80
    response = client.post(f"{PREFIX}/reset", json={"token": token, "new_password": password})
    assert response.status_code == 422
    assert token not in response.text and password not in response.text
    assert all("input" not in error for error in response.json()["detail"])

@pytest.mark.parametrize("provider,url", [("brevo", "https://api.brevo.com/v3/smtp/email"), ("resend", "https://api.resend.com/emails")])
def test_https_email_api_delivers_without_smtp_settings(monkeypatch, provider, url):
    import httpx

    for name in ("HOST", "USER", "PASSWORD"):
        monkeypatch.delenv(f"PASSWORD_RESET_SMTP_{name}", raising=False)
    monkeypatch.setenv("PASSWORD_RESET_ENABLED", "true")
    monkeypatch.setenv("PASSWORD_RESET_FRONTEND_ORIGIN", "https://reprocare.example.com")
    monkeypatch.setenv("PASSWORD_RESET_SMTP_FROM", "support@example.com")
    monkeypatch.setenv("PASSWORD_RESET_DELIVERY", provider)
    monkeypatch.setenv("PASSWORD_RESET_API_KEY", "")
    assert password_recovery.recovery_config() is None  # a key is required
    monkeypatch.setenv("PASSWORD_RESET_API_KEY", "fixture-key-not-real")
    config = password_recovery.recovery_config()
    assert config is not None and config.delivery == provider and "fixture-key-not-real" not in repr(config)

    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(201, json={"id": "fixture"})

    link = "https://reprocare.example.com/reset-password#token=abc"
    password_recovery.send_via_api(config, "patient@example.com", link, httpx.Client(transport=httpx.MockTransport(handler)))
    body = seen[0].read().decode()
    assert str(seen[0].url) == url and "patient@example.com" in body and "reset-password#token=abc" in body
    auth = seen[0].headers.get("api-key") or seen[0].headers.get("authorization")
    assert "fixture-key-not-real" in auth

    refused = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"message": "patient@example.com"})))
    with pytest.raises(OSError) as err:
        password_recovery.send_via_api(config, "patient@example.com", link, refused)
    assert "patient@example.com" not in str(err.value) and "401" in str(err.value)


def test_unknown_delivery_disables_recovery(recovery, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_DELIVERY", "carrier-pigeon")
    assert password_recovery.recovery_config() is None
    monkeypatch.setenv("PASSWORD_RESET_DELIVERY", "smtp")
    assert password_recovery.recovery_config() is not None
