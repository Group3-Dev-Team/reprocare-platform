"""Appointment requests: facility-scoped validation, duplicate protection, competing status changes,
patient rescheduling and the facility's responses. Uses the shared factories only."""

import itertools
import threading
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models import AppointmentRequest, Notification, Practitioner

_n = itertools.count(1)


def _future(days=10):
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.fixture()
def setup(make_facility, make_user):
    """A participating facility with two listed services, one practitioner, its staff member and a patient."""
    facility = make_facility(services=["antenatal", "postnatal"])
    other = make_facility()
    with SessionLocal() as db:
        n = next(_n)
        here = Practitioner(slug=f"prac-here-{n}", full_name="Dr Here", title="Midwife", specialty="Midwifery", town="Nairobi", facility_id=facility.id)
        there = Practitioner(slug=f"prac-there-{n}", full_name="Dr There", title="Midwife", specialty="Midwifery", town="Nairobi", facility_id=other.id)
        db.add_all([here, there])
        db.commit()
        here_slug, there_slug = here.slug, there.slug
    _, staff = make_user(role="facility_staff", facility=facility)
    patient_user, patient = make_user()
    return {"facility": facility, "here": here_slug, "there": there_slug, "staff": staff, "patient": patient, "patient_user": patient_user}


def _body(facility, **overrides):
    body = {"facility_slug": facility.slug, "preferred_date": _future(), "preferred_time": "morning", "contact_phone": "+254711000222"}
    body.update(overrides)
    return body


def test_request_confirm_and_cancel_lifecycle(client, setup):
    s = setup
    created = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], service_slug="antenatal", notes="First visit"))
    assert created.status_code == 201 and created.json()["status"] == "requested"
    ref = created.json()["reference"]

    staff_view = client.get("/api/facility/appointments?status=requested", headers=s["staff"]).json()["items"]
    assert [a["reference"] for a in staff_view] == [ref]
    assert staff_view[0]["patient"]["full_name"] == s["patient_user"].full_name

    confirmed = client.patch(f"/api/facility/appointments/{ref}", headers=s["staff"], json={"status": "confirmed", "facility_note": "See you at 10 am."})
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "confirmed"
    assert client.patch(f"/api/facility/appointments/{ref}", headers=s["staff"], json={"status": "declined"}).status_code == 400
    with SessionLocal() as db:
        titles = [n.title for n in db.query(Notification).filter_by(user_id=s["patient_user"].id)]
    assert any("confirmed" in t for t in titles)

    assert client.post(f"/api/me/appointments/{ref}/cancel", headers=s["patient"]).json()["status"] == "cancelled"


def test_roles_and_participation(client, setup, make_facility, make_user):
    s = setup
    assert client.post("/api/appointments", headers=s["staff"], json=_body(s["facility"])).status_code == 403
    assert client.get("/api/facility/appointments", headers=s["patient"]).status_code == 403
    closed = make_facility(accepts_appointment_requests=False)
    assert client.post("/api/appointments", headers=s["patient"], json=_body(closed)).status_code == 400
    ref = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date=_future(11))).json()["reference"]
    _, outsider = make_user(role="facility_staff", facility=closed)
    assert client.patch(f"/api/facility/appointments/{ref}", headers=outsider, json={"status": "confirmed"}).status_code == 404


def test_validation_of_dates_times_and_unknown_items(client, setup):
    s = setup
    assert client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date="2020-01-01")).status_code == 422
    assert client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_time="midnight")).status_code == 422
    assert client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], service_slug="not-a-service")).status_code == 422
    assert client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], practitioner_slug="nobody")).status_code == 422


def test_service_and_practitioner_must_belong_to_the_facility(client, setup):
    s = setup
    wrong_service = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], service_slug="fertility"))
    assert wrong_service.status_code == 422 and "does not list" in wrong_service.json()["detail"]
    assert client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], practitioner_slug=s["there"])).status_code == 422
    ok = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], service_slug="antenatal", practitioner_slug=s["here"], preferred_date=_future(12)))
    assert ok.status_code == 201
    assert ok.json()["service"]["slug"] == "antenatal" and ok.json()["practitioner"]["slug"] == s["here"]


def test_catalogue_service_accepted_when_facility_lists_none(client, make_facility, make_user):
    facility = make_facility()
    _, patient = make_user()
    created = client.post("/api/appointments", headers=patient, json=_body(facility, service_slug="fertility"))
    assert created.status_code == 201 and created.json()["service"]["slug"] == "fertility"


def test_concurrent_duplicate_requests_create_one_record(setup):
    s = setup
    body = _body(s["facility"], preferred_date=_future(20))
    barrier = threading.Barrier(4)
    codes = []

    def submit():
        local = TestClient(app)
        barrier.wait()
        codes.append(local.post("/api/appointments", headers=s["patient"], json=body).status_code)

    threads = [threading.Thread(target=submit) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201, 409, 409, 409]
    with SessionLocal() as db:
        count = db.query(AppointmentRequest).filter_by(facility_id=s["facility"].id, preferred_date=date.fromisoformat(body["preferred_date"])).count()
    assert count == 1


def test_parallel_confirm_and_cancel_agree(setup):
    s = setup
    setup_client = TestClient(app)
    ref = setup_client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date=_future(22))).json()["reference"]
    barrier = threading.Barrier(2)
    results = {}

    def confirm():
        local = TestClient(app)
        barrier.wait()
        results["confirm"] = local.patch(f"/api/facility/appointments/{ref}", headers=s["staff"], json={"status": "confirmed"}).status_code

    def cancel():
        local = TestClient(app)
        barrier.wait()
        results["cancel"] = local.post(f"/api/me/appointments/{ref}/cancel", headers=s["patient"]).status_code

    threads = [threading.Thread(target=confirm), threading.Thread(target=cancel)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    final = {a["reference"]: a["status"] for a in setup_client.get("/api/me/appointments", headers=s["patient"]).json()["items"]}[ref]
    assert results["cancel"] == 200 and final == "cancelled"
    assert results["confirm"] in (200, 400, 409)


def test_reschedule_returns_request_to_pending(client, setup):
    s = setup
    ref = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date=_future(30))).json()["reference"]
    assert client.patch(f"/api/facility/appointments/{ref}", headers=s["staff"], json={"status": "confirmed", "facility_note": "Ok"}).status_code == 200
    same = client.post(f"/api/me/appointments/{ref}/reschedule", headers=s["patient"], json={"preferred_date": _future(30), "preferred_time": "morning"})
    assert same.status_code == 400
    moved = client.post(f"/api/me/appointments/{ref}/reschedule", headers=s["patient"], json={"preferred_date": _future(31), "preferred_time": "evening"})
    assert moved.status_code == 200
    data = moved.json()
    assert data["status"] == "requested" and data["preferred_date"] == _future(31) and data["preferred_time"] == "evening" and data["facility_note"] == ""
    assert client.patch(f"/api/facility/appointments/{ref}", headers=s["staff"], json={"status": "confirmed"}).json()["status"] == "confirmed"


def test_reschedule_rules(client, setup, make_user):
    s = setup
    first = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date=_future(40))).json()["reference"]
    second = client.post("/api/appointments", headers=s["patient"], json=_body(s["facility"], preferred_date=_future(41))).json()["reference"]
    clash = client.post(f"/api/me/appointments/{second}/reschedule", headers=s["patient"], json={"preferred_date": _future(40), "preferred_time": "afternoon"})
    assert clash.status_code == 409
    past = client.post(f"/api/me/appointments/{first}/reschedule", headers=s["patient"], json={"preferred_date": "2020-01-01", "preferred_time": "morning"})
    assert past.status_code == 422
    client.post(f"/api/me/appointments/{first}/cancel", headers=s["patient"])
    assert client.post(f"/api/me/appointments/{first}/reschedule", headers=s["patient"], json={"preferred_date": _future(42), "preferred_time": "morning"}).status_code == 400
    _, stranger = make_user()
    assert client.post(f"/api/me/appointments/{second}/reschedule", headers=stranger, json={"preferred_date": _future(43), "preferred_time": "morning"}).status_code == 404
