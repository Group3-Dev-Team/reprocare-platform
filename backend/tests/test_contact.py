"""Contact Us messages (app/routes/content_routes.py) and their administration (app/routes/admin_routes.py).

These tests describe the current behaviour.
"""

import itertools

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import ContactMessage

_unique = itertools.count(1)


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


def _message(**fields):
    body = {"name": "Mary Achieng", "email": f"Mary.{next(_unique)}@Example.com", "message": "Please update the clinic opening hours."}
    body.update(fields)
    return body


def _send(client, headers=None, **fields):
    return client.post("/api/contact", headers=headers or {}, json=_message(**fields))


def _admin_items(client, headers, **params):
    response = client.get("/api/admin/contact-messages", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_anyone_can_send_a_message(client, admin_headers):
    response = _send(client, email="Visitor.Case@Example.com", name="  Mary Achieng  ")
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("MSG-")
    assert body["status"] == "new"

    stored = next(m for m in _admin_items(client, admin_headers)["items"] if m["reference"] == body["reference"])
    assert stored["email"] == "visitor.case@example.com"
    assert stored["name"] == "Mary Achieng"
    assert stored["topic"] == "general"
    assert stored["status"] == "new"


def test_signed_in_sender_is_linked_to_the_message(client, make_user):
    user, headers = make_user()
    reference = _send(client, headers, topic="listing_correction").json()["reference"]
    anonymous = _send(client).json()["reference"]
    with SessionLocal() as db:
        assert db.scalar(select(ContactMessage.user_id).where(ContactMessage.reference == reference)) == user.id
        assert db.scalar(select(ContactMessage.user_id).where(ContactMessage.reference == anonymous)) is None


def test_honeypot_field_rejects_the_message(client):
    response = _send(client, website="http://spam.example")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "change",
    [{"email": "not-an-email"}, {"message": "too short"}, {"name": "A"}, {"topic": "complaint"}, {"message": "x" * 4001}],
)
def test_invalid_messages_are_rejected(client, change):
    assert _send(client, **change).status_code == 422


def test_admin_lists_newest_first_with_pagination_envelope(client, admin_headers):
    older = _send(client).json()["reference"]
    newer = _send(client).json()["reference"]
    page = _admin_items(client, admin_headers)
    assert {"items", "total", "page", "page_size", "pages"} <= set(page)
    assert page["page"] == 1 and page["page_size"] == 20
    references = [m["reference"] for m in page["items"]]
    assert references.index(newer) < references.index(older)


def test_admin_updates_status_and_filters_by_it(client, admin_headers):
    reference = _send(client).json()["reference"]
    response = client.patch(f"/api/admin/contact-messages/{reference}", headers=admin_headers, json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json() == {"reference": reference, "status": "in_progress"}

    in_progress = [m["reference"] for m in _admin_items(client, admin_headers, status="in_progress")["items"]]
    new = [m["reference"] for m in _admin_items(client, admin_headers, status="new")["items"]]
    assert reference in in_progress and reference not in new

    resolved = client.patch(f"/api/admin/contact-messages/{reference}", headers=admin_headers, json={"status": "resolved"})
    assert resolved.json()["status"] == "resolved"


def test_admin_status_update_validation(client, admin_headers):
    reference = _send(client).json()["reference"]
    assert client.patch(f"/api/admin/contact-messages/{reference}", headers=admin_headers, json={"status": "closed"}).status_code == 422
    assert client.patch("/api/admin/contact-messages/MSG-NOPE00", headers=admin_headers, json={"status": "resolved"}).status_code == 404
    assert client.get("/api/admin/contact-messages", headers=admin_headers, params={"status": "closed"}).status_code == 422


def test_new_messages_are_counted_in_the_admin_overview(client, admin_headers):
    before = client.get("/api/admin/overview", headers=admin_headers).json()["contact_new"]
    _send(client)
    assert client.get("/api/admin/overview", headers=admin_headers).json()["contact_new"] == before + 1


def test_contact_administration_is_admin_only(client, make_user, make_facility):
    reference = _send(client).json()["reference"]
    patient = make_user()[1]
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    for headers, expected in (({}, 401), (patient, 403), (staff, 403)):
        assert client.get("/api/admin/contact-messages", headers=headers).status_code == expected
        assert client.patch(f"/api/admin/contact-messages/{reference}", headers=headers, json={"status": "resolved"}).status_code == expected
