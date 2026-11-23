"""Google sign-in tests. Google itself is faked, nothing is sent to Google."""

from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import delete, select

from app.config import settings
from app.database.session import SessionLocal
from app.models import GoogleIdentity, User, UserSession
from app.routes import auth_routes
from app.services import google_oidc, rate_limit

GOOGLE_START = "/api/auth/google/start"
GOOGLE_EXCHANGE = "/api/auth/google/exchange"
GOOGLE_LINK = "/api/auth/google/link"
PASSWORD = "TemporaryTestPassword1"
BROWSER_PROOF = "v" * 48


@pytest.fixture
def google(monkeypatch):
    # turn Google on with fake settings for the test only
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "configured-test-client")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "configured-test-placeholder")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "http://localhost:15173/auth/google/callback")
    monkeypatch.setattr(google_oidc, "_google_verifier", lambda: True)
    rate_limit.reset(
        "ip:google-start:testclient", "ip:google-exchange:testclient",
        "ip:google-link-start:testclient", "ip:google-link-exchange:testclient",
    )
    return monkeypatch


def start(client, intent="register"):
    response = client.post(GOOGLE_START, json={
        "intent": intent, "accept_terms": intent == "register",
        "challenge": google_oidc._challenge(BROWSER_PROOF),
    })
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    bundle = response.json()
    provider = urlsplit(bundle["url"])
    params = parse_qs(provider.query)
    assert provider.hostname == "accounts.google.com"
    assert params["state"] == [bundle["state"]]
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"] == [google_oidc._challenge(BROWSER_PROOF)]
    return bundle["state"], params["nonce"][0]


def exchange(client, state, verifier=BROWSER_PROOF):
    return client.post(GOOGLE_EXCHANGE, json={"state": state, "verifier": verifier, "code": "one-use-test-code"})


def claims(nonce, subject, email, **overrides):
    # what Google would send back about the person (faked)
    return {
        "nonce": nonce, "sub": subject, "name": "Software Test",
        "email": email, "email_verified": True, **overrides,
    }


def test_google_disabled_without_explicit_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "google_oauth_enabled", False)
    assert client.get("/api/auth/capabilities").json() == {"google": False}
    assert client.post(GOOGLE_START, json={"intent": "sign-in", "challenge": "v" * 43}).status_code == 503


def test_google_attempt_rejects_wrong_browser_proof_and_nonce(client, google):
    assert client.get("/api/auth/capabilities").json() == {"google": True}
    state, nonce = start(client)
    assert exchange(client, state, "q" * 48).status_code == 400
    google.setattr(google_oidc, "_verify_code", lambda *_: claims("unrelated-nonce", "nonce-test-sub", "nonce@example.com"))
    assert exchange(client, state).status_code == 400
    # the attempt was used up above, so even the right nonce fails now
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "nonce-test-sub", "nonce@example.com"))
    assert exchange(client, state).status_code == 400


def test_google_creates_session_for_stable_subject_and_patient_only(client, google):
    state, nonce = start(client)
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "stable-test-sub", "oauth-test-user@gmail.com", role="admin"))
    response = exchange(client, state)
    assert response.status_code == 200
    first = response.json()
    # Google sign up always makes a patient
    assert first["user"]["role"] == "patient"
    assert first["user"]["facility"] is None
    first_auth = {"Authorization": f"Bearer {first['token']}"}
    assert client.get("/api/auth/me", headers=first_auth).json()["id"] == first["user"]["id"]
    assert client.post("/api/auth/logout", headers=first_auth).status_code == 204
    assert client.get("/api/auth/me", headers=first_auth).status_code == 401

    # same Google account signs in to the same user, even if its email changed
    state, nonce = start(client, "sign-in")
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "stable-test-sub", "updated-test-email@gmail.com"))
    assert exchange(client, state).json()["user"]["id"] == first["user"]["id"]


def test_google_email_match_never_links_even_when_verified(client, google):
    registration = client.post("/api/auth/register", json={
        "email": "oauth-collision@gmail.com", "password": "FixturePassword1", "full_name": "Existing Account",
    })
    assert registration.status_code == 201
    state, nonce = start(client)
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "collision-test-sub", "oauth-collision@gmail.com"))
    assert exchange(client, state).status_code == 409
    with SessionLocal() as db:
        assert db.get(GoogleIdentity, "collision-test-sub") is None


def test_google_rejects_unverified_or_non_authoritative_registration_email(client, google):
    for index, (address, verified) in enumerate([("test@gmail.com", False), ("test@example.com", True)]):
        state, nonce = start(client)
        google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, f"untrusted-mail-{index}", address, email_verified=verified))
        assert exchange(client, state).status_code in {400, 409}
    # registering needs the terms accepted
    assert client.post(GOOGLE_START, json={"intent": "register", "challenge": "v" * 43}).status_code == 422


def password_account(client, email):
    response = client.post("/api/auth/register", json={
        "email": email, "password": PASSWORD, "full_name": "Password Account",
    })
    assert response.status_code == 201
    account = response.json()
    return {"Authorization": f"Bearer {account['token']}"}, account["user"]


def link_start(client, auth, password=PASSWORD):
    return client.post(f"{GOOGLE_LINK}/start", json={
        "current_password": password, "challenge": google_oidc._challenge(BROWSER_PROOF),
    }, headers=auth)


def link_proof(response):
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.json()
    params = parse_qs(urlsplit(data["url"]).query)
    assert params["prompt"] == ["select_account"]
    return {"state": data["state"], "code": "one-use-test-code", "verifier": BROWSER_PROOF}, params["nonce"][0]


def test_link_requires_password_and_exact_authenticated_browser_session(client, google):
    email = "same-session-link@gmail.com"
    headers, user = password_account(client, email)
    other, _ = password_account(client, "other-link-user@gmail.com")
    assert client.get(GOOGLE_LINK).status_code == 401
    assert link_start(client, {}).status_code == 401
    assert link_start(client, headers, "WrongTemporaryPassword1").status_code == 400
    assert client.get(GOOGLE_LINK, headers=headers).json() == {"available": True, "linked": False}

    proof, nonce = link_proof(link_start(client, headers))
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "safe-linked-sub", email, role="admin"))
    second_session = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["token"]
    same_account = {"Authorization": f"Bearer {second_session}"}
    # only the session that started the link can finish it
    assert client.post(GOOGLE_EXCHANGE, json=proof).status_code == 400
    assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=same_account).status_code == 400
    assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=other).status_code == 400
    assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=headers).status_code == 204
    assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=headers).status_code == 400
    assert client.get(GOOGLE_LINK, headers=headers).json() == {"available": True, "linked": True}
    assert link_start(client, headers).status_code == 409
    assert client.get("/api/auth/me", headers=headers).json()["id"] == user["id"]

    state, sign_in_nonce = start(client, "sign-in")
    google.setattr(google_oidc, "_verify_code", lambda *_: claims(sign_in_nonce, "safe-linked-sub", email, role="admin"))
    signed_in = exchange(client, state).json()["user"]
    assert signed_in["id"] == user["id"] and signed_in["role"] == "patient"


def test_link_rejects_unverified_or_mismatched_google_email(client, google):
    headers, _ = password_account(client, "authoritative-link@gmail.com")
    for email, verified, status in [
        ("authoritative-link@gmail.com", False, 400), ("new-link@gmail.com", True, 409),
    ]:
        proof, nonce = link_proof(link_start(client, headers))
        google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "wrong-email-link", email, email_verified=verified))
        assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=headers).status_code == status
    assert client.get(GOOGLE_LINK, headers=headers).json()["linked"] is False


def test_link_preserves_subject_already_assigned_to_another_account(client, google):
    original, owner = password_account(client, "existing-link@gmail.com")
    other, _ = password_account(client, "collision-link@gmail.com")
    for headers, email, expected in [
        (original, "existing-link@gmail.com", 204), (other, "collision-link@gmail.com", 409),
    ]:
        proof, nonce = link_proof(link_start(client, headers))
        google.setattr(google_oidc, "_verify_code", lambda *_: claims(nonce, "unique-link-sub", email))
        assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=headers).status_code == expected
    with SessionLocal() as db:
        assert db.get(GoogleIdentity, "unique-link-sub").user_id == owner["id"]


def test_link_aborts_when_session_is_revoked_during_google_exchange(client, google):
    email = "revoked-link@gmail.com"
    headers, user = password_account(client, email)
    proof, nonce = link_proof(link_start(client, headers))

    def verify_and_revoke(*_):
        # user gets signed out while they are on Google's page
        with SessionLocal() as db:
            db.execute(delete(UserSession).where(UserSession.user_id == user["id"]))
            db.commit()
        return claims(nonce, "revoked-link-sub", email)

    google.setattr(google_oidc, "_verify_code", verify_and_revoke)
    assert client.post(f"{GOOGLE_LINK}/exchange", json=proof, headers=headers).status_code == 400
    with SessionLocal() as db:
        assert db.get(GoogleIdentity, "revoked-link-sub") is None


def test_password_registration_rolls_back_if_session_cannot_be_written(client, monkeypatch):
    email = "atomic-registration@example.com"

    def fail_session(*_):
        raise RuntimeError("Simulate session write failure")

    monkeypatch.setattr(auth_routes, "create_session", fail_session)
    with pytest.raises(RuntimeError, match="Simulate session write failure"):
        client.post("/api/auth/register", json={"email": email, "password": "FixturePassword1", "full_name": "Atomic Test"})
    # no half made account is left behind
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == email)) is None