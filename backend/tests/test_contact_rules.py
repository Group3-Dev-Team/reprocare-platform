"""Contact rules added in SCRUM-11: submission rate limits, and topic/search filters for administrators."""

import itertools
from collections import defaultdict, deque

import pytest

from app.services import rate_limit

_unique = itertools.count(1)


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    """Each test starts with no recorded submissions (the limiter keeps counts in memory)."""
    monkeypatch.setattr(rate_limit, "_attempts", defaultdict(deque))


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


def _send(client, **fields):
    body = {"name": "Joy Wambui", "email": f"joy.{next(_unique)}@example.com", "message": "Please check the listing for my clinic."}
    body.update(fields)
    return client.post("/api/contact", json=body)


# --- Rate limiting ------------------------------------------------------------------------------


def test_one_email_is_limited_to_eight_messages(client):
    for _ in range(rate_limit.MAX_FAILURES_PER_ACCOUNT):
        assert _send(client, email="Repeat.Sender@Example.com").status_code == 201
    limited = _send(client, email="repeat.sender@example.com")  # same address, any capitalisation
    assert limited.status_code == 429
    assert "wait 15 minutes" in limited.json()["detail"]
    assert _send(client).status_code == 201  # someone else can still write


def test_one_address_is_limited_to_forty_messages(client):
    for _ in range(rate_limit.MAX_FAILURES_PER_ADDRESS):
        assert _send(client).status_code == 201
    limited = _send(client)
    assert limited.status_code == 429
    assert "several messages" in limited.json()["detail"]


def test_rejected_validation_does_not_use_up_the_limit(client):
    for _ in range(rate_limit.MAX_FAILURES_PER_ACCOUNT + 2):
        assert _send(client, email="careful@example.com", message="short").status_code == 422
    assert _send(client, email="careful@example.com").status_code == 201


def test_contact_limits_do_not_affect_sign_in_limits(client, make_user):
    make_user(email="limits.user@example.com", password="Secret123")
    for _ in range(rate_limit.MAX_FAILURES_PER_ACCOUNT):
        _send(client, email="limits.user@example.com")
    assert _send(client, email="limits.user@example.com").status_code == 429
    signed_in = client.post("/api/auth/login", json={"email": "limits.user@example.com", "password": "Secret123"})
    assert signed_in.status_code == 200
    # and the sign-in limiter still answers with its own message
    for _ in range(rate_limit.MAX_FAILURES_PER_ACCOUNT):
        client.post("/api/auth/login", json={"email": "limits.user@example.com", "password": "Wrong1234"})
    blocked = client.post("/api/auth/login", json={"email": "limits.user@example.com", "password": "Wrong1234"})
    assert blocked.status_code == 429 and "sign-in attempts" in blocked.json()["detail"]


# --- Administrator filters -----------------------------------------------------------------------


def _references(client, headers, **params):
    response = client.get("/api/admin/contact-messages", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return {m["reference"] for m in response.json()["items"]}


def test_topic_filter(client, admin_headers):
    privacy = _send(client, topic="privacy").json()["reference"]
    technical = _send(client, topic="technical").json()["reference"]
    found = _references(client, admin_headers, topic="privacy")
    assert privacy in found and technical not in found
    assert client.get("/api/admin/contact-messages", headers=admin_headers, params={"topic": "complaint"}).status_code == 422


def test_text_search_covers_name_email_message_and_reference(client, admin_headers):
    token = f"srch{next(_unique)}z"
    by_name = _send(client, name=f"Name {token.upper()}").json()["reference"]
    by_email = _send(client, email=f"{token}@example.com").json()["reference"]
    by_message = _send(client, message=f"The opening hours for {token} clinic are wrong.").json()["reference"]
    other = _send(client).json()["reference"]

    found = _references(client, admin_headers, q=token)
    assert {by_name, by_email, by_message} <= found and other not in found
    assert _references(client, admin_headers, q=other.lower()) == {other}


def test_search_treats_percent_and_underscore_literally(client, admin_headers):
    literal = _send(client, message="The clinic says it is 100% free_of_charge today.").json()["reference"]
    plain = _send(client, message="The clinic says it is 100 percent free today.").json()["reference"]
    found = _references(client, admin_headers, q="100%")
    assert literal in found and plain not in found
    assert _references(client, admin_headers, q="free_of") >= {literal}
    assert plain not in _references(client, admin_headers, q="free_of")


def test_filters_combine_with_status_and_keep_the_list_shape(client, admin_headers):
    token = f"combo{next(_unique)}z"
    new = _send(client, topic="feedback", message=f"Feedback about {token} service.").json()["reference"]
    done = _send(client, topic="feedback", message=f"More feedback about {token} service.").json()["reference"]
    client.patch(f"/api/admin/contact-messages/{done}", headers=admin_headers, json={"status": "resolved"})

    assert _references(client, admin_headers, q=token, topic="feedback", status="resolved") == {done}
    assert _references(client, admin_headers, q=token, topic="feedback", status="new") == {new}
    assert _references(client, admin_headers, q=token, topic="privacy") == set()
    page = client.get("/api/admin/contact-messages", headers=admin_headers, params={"q": token}).json()
    assert set(page) == {"items", "total", "page", "page_size", "pages"} and page["total"] == 2
    assert client.get("/api/admin/contact-messages", headers=admin_headers, params={"q": "x" * 101}).status_code == 422


def test_filters_are_admin_only(client, make_user):
    patient = make_user()[1]
    assert client.get("/api/admin/contact-messages", params={"topic": "privacy"}).status_code == 401
    assert client.get("/api/admin/contact-messages", headers=patient, params={"q": "a"}).status_code == 403
