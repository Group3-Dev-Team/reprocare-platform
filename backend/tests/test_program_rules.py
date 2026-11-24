"""Programme rules added in SCRUM-11: capacity, dates, times, location, services, cancellation notices,
attendance and safe slugs."""

import itertools
from datetime import date, timedelta

import pytest

from app.routes import program_routes

_unique = itertools.count(1)


def _day(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


def _body(**fields):
    body = {
        "title": f"Outreach clinic rq{next(_unique)}x",
        "program_type": "outreach",
        "organizer_name": "County Health Office",
        "venue": "Market Grounds",
        "town": "Machakos",
        "county": "Machakos",
        "start_date": _day(14),
        "start_time": "09:00",
        "end_time": "13:00",
        "capacity": 5,
    }
    body.update(fields)
    return body


@pytest.fixture()
def create_program(client, admin_headers):
    def factory(**fields):
        response = client.post("/api/admin/programs", headers=admin_headers, json=_body(**fields))
        assert response.status_code == 201, response.text
        return response.json()

    return factory


def _register(client, headers, slug):
    response = client.post(f"/api/programs/{slug}/registrations", headers=headers, json={"full_name": "Faith Njeri", "phone": "+254711222333", "consent": True})
    assert response.status_code == 201, response.text
    return response.json()["reference"]


def _patch(client, headers, slug, **body):
    return client.patch(f"/api/admin/programs/{slug}", headers=headers, json=body)


# --- 1. Capacity ----------------------------------------------------------------------------------


def test_capacity_cannot_drop_below_active_registrations(client, create_program, make_user, admin_headers):
    program = create_program(capacity=5)
    slug = program["slug"]
    _register(client, make_user()[1], slug)
    _register(client, make_user()[1], slug)
    leaver = make_user()[1]
    client.post(f"/api/me/registrations/{_register(client, leaver, slug)}/cancel", headers=leaver)

    refused = _patch(client, admin_headers, slug, capacity=1)
    assert refused.status_code == 409
    assert "2 people" in refused.json()["detail"]
    assert client.get(f"/api/programs/{slug}").json()["capacity"] == 5

    # cancelled registrations do not count, and capacity equal to the active registrations is allowed
    allowed = _patch(client, admin_headers, slug, capacity=2)
    assert allowed.status_code == 200
    assert (allowed.json()["capacity"], allowed.json()["spaces_left"]) == (2, 0)


# --- 2. Dates, times and coordinates ---------------------------------------------------------------


def test_dates_more_than_two_years_ahead_are_rejected(client, admin_headers, create_program):
    assert client.post("/api/admin/programs", headers=admin_headers, json=_body(start_date=_day(731))).status_code == 422
    assert client.post("/api/admin/programs", headers=admin_headers, json=_body(start_date=_day(730))).status_code == 201
    program = create_program()
    assert _patch(client, admin_headers, program["slug"], start_date=_day(800)).status_code == 422


def test_programme_with_registrations_cannot_move_into_the_past(client, create_program, make_user, admin_headers):
    booked = create_program()
    _register(client, make_user()[1], booked["slug"])
    refused = _patch(client, admin_headers, booked["slug"], start_date=_day(-1))
    assert refused.status_code == 409
    assert client.get(f"/api/programs/{booked['slug']}").json()["start_date"] == _day(14)
    assert _patch(client, admin_headers, booked["slug"], start_date=_day(30)).status_code == 200

    # without registrations an administrator may still record a past date (existing behaviour)
    empty = create_program()
    assert _patch(client, admin_headers, empty["slug"], start_date=_day(-1)).status_code == 200


@pytest.mark.parametrize(
    "start, end",
    [("9:00 am", "1:00 pm"), ("09:00", "13:30"), ("12:00 pm", "12:30 PM"), ("11:45 a.m.", "2:00 p.m."), ("7:05", "19:00")],
)
def test_accepted_time_formats(client, admin_headers, start, end):
    response = client.post("/api/admin/programs", headers=admin_headers, json=_body(start_time=f" {start} ", end_time=end))
    assert response.status_code == 201, response.text
    assert (response.json()["start_time"], response.json()["end_time"]) == (start, end)


@pytest.mark.parametrize(
    "start, end",
    [("noon", "13:00"), ("25:00", "26:00"), ("13:00 pm", "14:00"), ("9:60", "10:00"), ("0:30 am", "1:00 am"),
     ("14:00", "13:00"), ("10:00", "10:00"), ("1:00 pm", "11:00 am")],
)
def test_invalid_or_reversed_times_are_rejected(client, admin_headers, start, end):
    assert client.post("/api/admin/programs", headers=admin_headers, json=_body(start_time=start, end_time=end)).status_code == 422


@pytest.mark.parametrize(
    "location",
    [{"latitude": -1.29}, {"longitude": 36.82}, {"latitude": 51.5, "longitude": -0.12}, {"latitude": -1.29, "longitude": 50.0}],
)
def test_invalid_locations_are_rejected(client, admin_headers, location):
    assert client.post("/api/admin/programs", headers=admin_headers, json=_body(**location)).status_code == 422


def test_location_in_kenya_is_stored(create_program):
    program = create_program(latitude=-1.2921, longitude=36.8219)
    assert (program["latitude"], program["longitude"]) == (-1.2921, 36.8219)


# --- 3. Services ----------------------------------------------------------------------------------


def test_unknown_service_is_rejected(client, admin_headers, create_program):
    refused = client.post("/api/admin/programs", headers=admin_headers, json=_body(service_slug="aromatherapy"))
    assert refused.status_code == 400
    assert "aromatherapy" in refused.json()["detail"]
    assert create_program(service_slug="contraception")["service"]["slug"] == "contraception"
    assert create_program(service_slug=None)["service"] is None


# --- 4. Cancellation notices ----------------------------------------------------------------------


def _titles(client, headers):
    return [n["title"] for n in client.get("/api/me/notifications", headers=headers).json()["items"]]


def test_cancelling_a_programme_notifies_active_registrants_once(client, create_program, make_user, admin_headers):
    program = create_program()
    slug = program["slug"]
    active = make_user()[1]
    reference = _register(client, active, slug)
    left = make_user()[1]
    client.post(f"/api/me/registrations/{_register(client, left, slug)}/cancel", headers=left)
    bystander = make_user()[1]

    assert _patch(client, admin_headers, slug, status="cancelled").status_code == 200

    notes = client.get("/api/me/notifications", headers=active).json()["items"]
    cancelled = [n for n in notes if n["title"] == "Programme cancelled"]
    assert len(cancelled) == 1
    assert program["title"] in cancelled[0]["body"] and reference in cancelled[0]["body"]
    assert cancelled[0]["link"] == "/dashboard/registrations"
    assert "Programme cancelled" not in _titles(client, left)
    assert "Programme cancelled" not in _titles(client, bystander)

    # the registration itself is kept, so re-publishing restores it
    mine = client.get("/api/me/registrations", headers=active).json()
    assert [(r["status"], r["program"]["status"]) for r in mine] == [("registered", "cancelled")]

    # saving the same status again does not send a second notice
    _patch(client, admin_headers, slug, status="cancelled")
    assert _titles(client, active).count("Programme cancelled") == 1


def test_other_status_changes_send_no_cancellation_notice(client, create_program, make_user, admin_headers):
    program = create_program()
    patient = make_user()[1]
    _register(client, patient, program["slug"])
    _patch(client, admin_headers, program["slug"], status="draft")
    _patch(client, admin_headers, program["slug"], capacity=9)
    assert "Programme cancelled" not in _titles(client, patient)


# --- 5. Attendance --------------------------------------------------------------------------------


def _attendance(client, headers, slug, reference, status):
    return client.patch(f"/api/admin/programs/{slug}/registrations/{reference}", headers=headers, json={"status": status})


def test_admin_marks_and_unmarks_attendance(client, create_program, make_user, admin_headers):
    program = create_program(start_date=_day(0))  # the programme takes place today
    patient = make_user()[1]
    reference = _register(client, patient, program["slug"])

    marked = _attendance(client, admin_headers, program["slug"], reference, "attended")
    assert marked.status_code == 200
    assert (marked.json()["reference"], marked.json()["status"]) == (reference, "attended")
    assert "program" not in marked.json()
    assert client.get("/api/me/registrations", headers=patient).json()[0]["status"] == "attended"
    # an attended place still counts against capacity
    assert client.get(f"/api/programs/{program['slug']}").json()["registered"] == 1
    # the patient can no longer cancel an attended place (existing rule: only active registrations)
    assert client.post(f"/api/me/registrations/{reference}/cancel", headers=patient).status_code == 400

    undone = _attendance(client, admin_headers, program["slug"], reference, "registered")
    assert undone.json()["status"] == "registered"


def test_attendance_cannot_be_recorded_before_the_programme_date(client, create_program, make_user, admin_headers):
    program = create_program(start_date=_day(3))
    reference = _register(client, make_user()[1], program["slug"])

    refused = _attendance(client, admin_headers, program["slug"], reference, "attended")
    assert refused.status_code == 400
    assert "from the programme date" in refused.json()["detail"]
    rows = client.get(f"/api/admin/programs/{program['slug']}/registrations", headers=admin_headers).json()
    assert [r["status"] for r in rows] == ["registered"]

    # confirming the existing "registered" status is a harmless correction and stays allowed
    assert _attendance(client, admin_headers, program["slug"], reference, "registered").status_code == 200


def test_attendance_for_a_programme_that_has_already_taken_place(client, create_program, make_user, admin_headers):
    program = create_program(start_date=_day(0))
    reference = _register(client, make_user()[1], program["slug"])
    # time passes: the programme is now historical (the API itself refuses to move a booked programme into the past)
    from app.database.session import SessionLocal
    from app.models import CommunityProgram

    with SessionLocal() as db:
        db.get(CommunityProgram, program["id"]).start_date = date.today() - timedelta(days=5)
        db.commit()

    assert _attendance(client, admin_headers, program["slug"], reference, "attended").json()["status"] == "attended"
    # an administrator can correct a wrong mark afterwards, and re-mark it
    assert _attendance(client, admin_headers, program["slug"], reference, "registered").json()["status"] == "registered"
    assert _attendance(client, admin_headers, program["slug"], reference, "attended").json()["status"] == "attended"
    # the historical programme is still browsable with include_past
    assert client.get(f"/api/programs/{program['slug']}").json()["is_past"] is True


def test_attendance_mark_can_be_undone_after_a_programme_is_postponed(client, create_program, make_user, admin_headers):
    program = create_program(start_date=_day(0))
    reference = _register(client, make_user()[1], program["slug"])
    assert _attendance(client, admin_headers, program["slug"], reference, "attended").status_code == 200
    assert _patch(client, admin_headers, program["slug"], start_date=_day(7)).status_code == 200

    assert _attendance(client, admin_headers, program["slug"], reference, "registered").status_code == 200
    assert _attendance(client, admin_headers, program["slug"], reference, "attended").status_code == 400


def test_attendance_validation(client, create_program, make_user, admin_headers):
    program = create_program()
    other = create_program()
    patient = make_user()[1]
    reference = _register(client, patient, program["slug"])

    assert _attendance(client, admin_headers, program["slug"], reference, "cancelled").status_code == 422
    assert _attendance(client, admin_headers, other["slug"], reference, "attended").status_code == 404
    assert _attendance(client, admin_headers, "no-such-programme", reference, "attended").status_code == 404
    assert _attendance(client, admin_headers, program["slug"], "REG-NOPE00", "attended").status_code == 404

    client.post(f"/api/me/registrations/{reference}/cancel", headers=patient)
    assert _attendance(client, admin_headers, program["slug"], reference, "attended").status_code == 400


def test_attendance_is_admin_only(client, create_program, make_user, make_facility):
    program = create_program()
    patient = make_user()[1]
    reference = _register(client, patient, program["slug"])
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    for headers, expected in (({}, 401), (patient, 403), (staff, 403)):
        assert _attendance(client, headers, program["slug"], reference, "attended").status_code == expected


# --- 6. Slug collisions ---------------------------------------------------------------------------


def test_slug_collision_at_insert_is_retried(client, admin_headers, create_program, monkeypatch):
    first = create_program(title="Breast screening week", town="Nyeri")
    real = program_routes._free_program_slug
    calls = []

    def stale_then_real(db, base):
        # The first lookup behaves as if it ran just before another administrator saved the same slug.
        calls.append(base)
        return first["slug"] if len(calls) == 1 else real(db, base)

    monkeypatch.setattr(program_routes, "_free_program_slug", stale_then_real)
    response = client.post("/api/admin/programs", headers=admin_headers, json=_body(title="Breast screening week", town="Nyeri"))
    assert response.status_code == 201, response.text
    assert response.json()["slug"] == f"{first['slug']}-2"
    assert len(calls) == 2


def test_repeated_slug_collisions_give_a_clear_conflict(client, admin_headers, create_program, monkeypatch):
    taken = create_program()["slug"]
    monkeypatch.setattr(program_routes, "_free_program_slug", lambda db, base: taken)
    response = client.post("/api/admin/programs", headers=admin_headers, json=_body())
    assert response.status_code == 409
    assert "try again" in response.json()["detail"]
