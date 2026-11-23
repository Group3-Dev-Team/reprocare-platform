"""ReproCare patient reviews: submission, moderation, publication, facility replies and listings."""

import pytest

from app.database.session import SessionLocal
from app.models import Notification

BODY = {"rating": 4, "title": "Helpful nurse", "body": "The nurse explained the screening clearly and I was done within twenty minutes.", "consent": True}


@pytest.fixture()
def setup(make_facility, make_user):
    facility = make_facility(services=["cervical"])
    other = make_facility()
    patient_user, patient = make_user()
    _, staff = make_user(role="facility_staff", facility=facility)
    _, admin = make_user(role="admin")
    return {"facility": facility, "other": other, "patient": patient, "patient_user": patient_user, "staff": staff, "admin": admin}


def test_review_is_hidden_until_published(client, setup):
    s = setup
    created = client.post(f"/api/facilities/{s['facility'].slug}/reviews", headers=s["patient"], json={**BODY, "service_slug": "cervical"})
    assert created.status_code == 201 and created.json()["status"] == "pending"
    rid = created.json()["id"]
    assert rid not in [r["id"] for r in client.get(f"/api/facilities/{s['facility'].slug}/reviews").json()["items"]]
    assert client.post(f"/api/facilities/{s['facility'].slug}/reviews", headers=s["patient"], json=BODY).status_code == 409

    pending = client.get("/api/admin/reviews?status=pending", headers=s["admin"]).json()["items"]
    assert rid in [r["id"] for r in pending]
    assert client.post(f"/api/admin/reviews/{rid}/moderate", headers=s["admin"], json={"decision": "published"}).status_code == 200

    public = client.get(f"/api/facilities/{s['facility'].slug}/reviews").json()
    assert rid in [r["id"] for r in public["items"]] and public["distribution"]["4"] == 1
    assert rid not in [r["id"] for r in client.get(f"/api/facilities/{s['other'].slug}/reviews").json()["items"]]
    assert rid in [r["id"] for r in client.get("/api/reviews").json()["items"]]
    assert client.get("/api/me/reviews", headers=s["patient"]).json()[0]["status"] == "published"
    with SessionLocal() as db:
        assert db.query(Notification).filter_by(user_id=s["patient_user"].id).count() == 1


def test_facility_reply_and_rejection(client, setup, make_user):
    s = setup
    rid = client.post(f"/api/facilities/{s['facility'].slug}/reviews", headers=s["patient"], json=BODY).json()["id"]
    # a reply is only possible once published, and only by the facility's own staff
    assert client.put(f"/api/facility/reviews/{rid}/reply", headers=s["staff"], json={"reply": "Thank you."}).status_code == 404
    client.post(f"/api/admin/reviews/{rid}/moderate", headers=s["admin"], json={"decision": "published"})
    _, outsider = make_user(role="facility_staff", facility=s["other"])
    assert client.put(f"/api/facility/reviews/{rid}/reply", headers=outsider, json={"reply": "Hello"}).status_code == 404
    reply = client.put(f"/api/facility/reviews/{rid}/reply", headers=s["staff"], json={"reply": "Thank you for your feedback."})
    assert reply.status_code == 200 and reply.json()["facility_reply"] == "Thank you for your feedback."
    assert [r["id"] for r in client.get("/api/facility/reviews", headers=s["staff"]).json()] == [rid]

    _, second = make_user()
    rid2 = client.post(f"/api/facilities/{s['facility'].slug}/reviews", headers=second, json=BODY).json()["id"]
    rejected = client.post(f"/api/admin/reviews/{rid2}/moderate", headers=s["admin"], json={"decision": "rejected", "note": "Contains a name."})
    assert rejected.json()["status"] == "rejected" and rejected.json()["moderation_note"] == "Contains a name."


def test_validation_and_permissions(client, setup):
    s = setup
    slug = s["facility"].slug
    assert client.post(f"/api/facilities/{slug}/reviews", headers=s["patient"], json={**BODY, "consent": False}).status_code == 400
    assert client.post(f"/api/facilities/{slug}/reviews", headers=s["patient"], json={**BODY, "service_slug": "teleportation"}).status_code == 422
    assert client.post(f"/api/facilities/{slug}/reviews", headers=s["staff"], json=BODY).status_code == 403
    assert client.post(f"/api/facilities/{slug}/reviews", json=BODY).status_code == 401
    assert client.post("/api/facilities/missing/reviews", headers=s["patient"], json=BODY).status_code == 404
    assert client.get("/api/admin/reviews", headers=s["staff"]).status_code == 403
