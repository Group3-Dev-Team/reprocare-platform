"""Close my account: confirmation, signing out everywhere and removing personal data."""

from datetime import date, timedelta

from app.database.session import SessionLocal
from app.models import AppointmentRequest, Review, User


def _register(client, n):
    email = f"closure{n}@example.com"
    r = client.post("/api/auth/register", json={"full_name": f"Closure Tester{n}", "email": email, "password": "Secret123", "phone": "+254711000999"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, email, r.json()["user"]


def test_closing_requires_matching_email_and_password(client):
    headers, email, _ = _register(client, 1)
    assert client.post("/api/auth/me/close", headers=headers, json={"confirm_email": "other@example.com", "password": "Secret123"}).status_code == 400
    assert client.post("/api/auth/me/close", headers=headers, json={"confirm_email": email, "password": "wrong-pass"}).status_code == 400
    assert client.post("/api/auth/me/close", headers=headers, json={"confirm_email": email}).status_code == 400
    assert client.get("/api/auth/me", headers=headers).status_code == 200  # still open


def test_closing_revokes_sessions_and_removes_personal_data(client, make_facility, make_user):
    facility = make_facility()
    _, staff = make_user(role="facility_staff", facility=facility)
    headers, email, user = _register(client, 2)
    second = client.post("/api/auth/login", json={"email": email, "password": "Secret123"}).json()["token"]
    when = (date.today() + timedelta(days=9)).isoformat()
    ref = client.post("/api/appointments", headers=headers, json={
        "facility_slug": facility.slug, "preferred_date": when, "preferred_time": "morning", "contact_phone": "+254711000999", "notes": "private note",
    }).json()["reference"]
    assert client.put(f"/api/me/saved/{facility.slug}", headers=headers).status_code == 204
    review = client.post(f"/api/facilities/{facility.slug}/reviews", headers=headers, json={
        "rating": 4, "title": "Kind staff", "body": "Clear explanations and short wait at reception today.", "consent": True,
    })
    assert review.status_code == 201

    closed = client.post("/api/auth/me/close", headers=headers, json={"confirm_email": email.upper(), "password": "Secret123"})
    assert closed.status_code == 204

    # every session is gone and the old details don't work
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {second}"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "Secret123"}).status_code == 401

    with SessionLocal() as db:
        row = db.get(User, user["id"])
        assert row.is_active is False and row.full_name == "Closed account" and row.phone is None
        assert row.email.endswith("@closed.invalid")
        appointment = db.query(AppointmentRequest).filter_by(reference=ref).one()
        assert appointment.status == "cancelled" and appointment.contact_phone == "" and appointment.notes == ""
        assert db.query(Review).filter_by(id=review.json()["id"]).first() is None  # pending review removed

    # the clinic still sees the cancelled request, but without the person's name
    staff_view = {a["reference"]: a for a in client.get("/api/facility/appointments?status=cancelled&page_size=40", headers=staff).json()["items"]}
    assert staff_view[ref]["patient"]["full_name"] == "Closed account"

    # the same email can sign up again
    assert client.post("/api/auth/register", json={"full_name": "New Person", "email": email, "password": "Secret123"}).status_code == 201


def test_staff_cannot_close_their_own_account(client, make_facility, make_user):
    staff_user, staff = make_user(role="facility_staff", facility=make_facility())
    r = client.post("/api/auth/me/close", headers=staff, json={"confirm_email": staff_user.email, "password": "Secret123"})
    assert r.status_code == 403