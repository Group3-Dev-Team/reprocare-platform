"""Community programmes: public browsing, patient registration and cancellation, administrator management.

These tests describe the behaviour of app/routes/program_routes.py as it stands.
"""

import itertools
from datetime import date, timedelta

import pytest

_unique = itertools.count(1)


def _day(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


@pytest.fixture()
def create_program(client, admin_headers):
    """Create a programme through the admin API. Each title carries a unique token so searches find only it."""

    def factory(**fields):
        token = f"zq{next(_unique)}x"
        body = {
            "title": f"Cervical screening day {token}",
            "program_type": "screening",
            "organizer_name": "County Health Office",
            "venue": "Community Hall",
            "town": "Nakuru",
            "county": "Nakuru",
            "start_date": _day(10),
            "start_time": "09:00",
            "end_time": "15:00",
            "capacity": 5,
        }
        body.update(fields)
        response = client.post("/api/admin/programs", headers=admin_headers, json=body)
        assert response.status_code == 201, response.text
        return response.json(), token

    return factory


def _register(client, headers, slug, **fields):
    body = {"full_name": "Amina Otieno", "phone": "+254711000111", "consent": True}
    body.update(fields)
    return client.post(f"/api/programs/{slug}/registrations", headers=headers, json=body)


# --- Public browsing -----------------------------------------------------------------------------


def test_admin_created_programme_is_listed_and_viewable(client, create_program):
    program, token = create_program(service_slug="cervical", capacity=7)
    assert program["status"] == "published"
    assert program["registered"] == 0 and program["spaces_left"] == 7
    assert program["is_past"] is False

    listed = client.get("/api/programs", params={"q": token})
    assert listed.status_code == 200
    assert [p["slug"] for p in listed.json()["items"]] == [program["slug"]]

    detail = client.get(f"/api/programs/{program['slug']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == program["title"]


def test_unknown_programme_is_404(client):
    assert client.get("/api/programs/no-such-programme").status_code == 404


def test_same_title_and_town_get_distinct_slugs(client, create_program):
    first, token = create_program()
    second, _ = create_program(title=first["title"])
    assert second["slug"] == f"{first['slug']}-2"


def test_draft_and_cancelled_programmes_are_hidden_from_the_public(client, create_program):
    draft, draft_token = create_program(status="draft")
    cancelled, cancelled_token = create_program(status="cancelled")
    for program, token in ((draft, draft_token), (cancelled, cancelled_token)):
        assert client.get("/api/programs", params={"q": token}).json()["items"] == []
        assert client.get(f"/api/programs/{program['slug']}").status_code == 404


def test_past_programmes_appear_only_when_requested(client, create_program):
    past, token = create_program(start_date=_day(-3))
    assert client.get("/api/programs", params={"q": token}).json()["items"] == []
    items = client.get("/api/programs", params={"q": token, "include_past": True}).json()["items"]
    assert [p["slug"] for p in items] == [past["slug"]]
    assert items[0]["is_past"] is True


def test_list_filters(client, create_program):
    free, token_free = create_program(program_type="testing", cost_type="free", town="Kisumu", service_slug="hiv")
    paid, token_paid = create_program(program_type="education", cost_type="paid", town="Eldoret")

    def slugs(token, **params):
        return [p["slug"] for p in client.get("/api/programs", params={"q": token, **params}).json()["items"]]

    assert slugs(token_free, program_type="testing") == [free["slug"]]
    assert slugs(token_free, program_type="education") == []
    assert slugs(token_free, cost_type="subsidised,free") == [free["slug"]]
    assert slugs(token_paid, cost_type="free") == []
    assert slugs(token_free, town="kisumu") == [free["slug"]]
    assert slugs(token_free, service="hiv") == [free["slug"]]
    assert slugs(token_paid, service="hiv") == []
    assert client.get("/api/programs", params={"program_type": "surgery"}).status_code == 422


# --- Registration ---------------------------------------------------------------------------------


def test_registration_requires_a_signed_in_patient(client, create_program, make_user, make_facility):
    program, _ = create_program()
    slug = program["slug"]
    assert _register(client, {}, slug).status_code == 401
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    admin = make_user(role="admin")[1]
    assert _register(client, staff, slug).status_code == 403
    assert _register(client, admin, slug).status_code == 403


def test_registration_requires_consent_and_valid_details(client, create_program, make_user):
    program, _ = create_program()
    patient = make_user()[1]
    assert _register(client, patient, program["slug"], consent=False).status_code == 400
    assert _register(client, patient, program["slug"], full_name="A").status_code == 422
    assert _register(client, patient, program["slug"], phone="123").status_code == 422


def test_patient_registers_and_sees_registration_and_notification(client, create_program, make_user):
    program, _ = create_program(capacity=3)
    patient = make_user()[1]

    response = _register(client, patient, program["slug"], full_name="  Amina Otieno  ")
    assert response.status_code == 201, response.text
    registration = response.json()
    assert registration["reference"].startswith("REG-")
    assert registration["status"] == "registered"
    assert registration["full_name"] == "Amina Otieno"
    assert registration["program"]["slug"] == program["slug"]

    mine = client.get("/api/me/registrations", headers=patient)
    assert mine.status_code == 200
    assert [r["reference"] for r in mine.json()] == [registration["reference"]]

    detail = client.get(f"/api/programs/{program['slug']}").json()
    assert detail["registered"] == 1 and detail["spaces_left"] == 2

    notes = client.get("/api/me/notifications", headers=patient).json()["items"]
    assert any(n["title"] == "Registration confirmed" and registration["reference"] in n["body"] and n["link"] == "/dashboard/registrations" for n in notes)


def test_registering_twice_is_a_conflict(client, create_program, make_user):
    program, _ = create_program()
    patient = make_user()[1]
    reference = _register(client, patient, program["slug"]).json()["reference"]
    again = _register(client, patient, program["slug"])
    assert again.status_code == 409
    assert reference in again.json()["detail"]


def test_full_programme_refuses_registration(client, create_program, make_user):
    program, _ = create_program(capacity=1)
    assert _register(client, make_user()[1], program["slug"]).status_code == 201
    full = _register(client, make_user()[1], program["slug"])
    assert full.status_code == 409
    assert "full" in full.json()["detail"]


def test_registration_closed_for_past_programme(client, create_program, make_user):
    program, _ = create_program(start_date=_day(-1))
    assert _register(client, make_user()[1], program["slug"]).status_code == 400


def test_registration_for_unpublished_programme_is_404(client, create_program, make_user, admin_headers):
    program, _ = create_program()
    assert client.patch(f"/api/admin/programs/{program['slug']}", headers=admin_headers, json={"status": "cancelled"}).status_code == 200
    assert _register(client, make_user()[1], program["slug"]).status_code == 404


# --- Cancellation ---------------------------------------------------------------------------------


def test_cancelling_frees_the_space(client, create_program, make_user):
    program, _ = create_program(capacity=1)
    first = make_user()[1]
    reference = _register(client, first, program["slug"]).json()["reference"]

    cancelled = client.post(f"/api/me/registrations/{reference}/cancel", headers=first)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get(f"/api/programs/{program['slug']}").json()["spaces_left"] == 1

    assert client.post(f"/api/me/registrations/{reference}/cancel", headers=first).status_code == 400
    assert _register(client, make_user()[1], program["slug"]).status_code == 201


def test_reregistering_after_cancelling_reuses_the_reference(client, create_program, make_user):
    program, _ = create_program()
    patient = make_user()[1]
    reference = _register(client, patient, program["slug"]).json()["reference"]
    client.post(f"/api/me/registrations/{reference}/cancel", headers=patient)

    again = _register(client, patient, program["slug"], phone="+254722000222")
    assert again.status_code == 201
    assert again.json()["reference"] == reference
    assert again.json()["status"] == "registered"
    assert again.json()["phone"] == "+254722000222"


def test_patients_cannot_cancel_someone_elses_registration(client, create_program, make_user):
    program, _ = create_program()
    owner = make_user()[1]
    reference = _register(client, owner, program["slug"]).json()["reference"]
    assert client.post(f"/api/me/registrations/{reference}/cancel", headers=make_user()[1]).status_code == 404
    assert client.post(f"/api/me/registrations/{reference}/cancel").status_code == 401


# --- Administrators -------------------------------------------------------------------------------


def test_admin_sees_all_programmes_and_registrations(client, create_program, make_user, admin_headers):
    published, _ = create_program()
    draft, _ = create_program(status="draft")
    slugs = {p["slug"] for p in client.get("/api/admin/programs", headers=admin_headers).json()}
    assert {published["slug"], draft["slug"]} <= slugs

    _register(client, make_user()[1], published["slug"], full_name="Grace Wanjiru")
    rows = client.get(f"/api/admin/programs/{published['slug']}/registrations", headers=admin_headers).json()
    assert [(r["full_name"], r["status"]) for r in rows] == [("Grace Wanjiru", "registered")]
    assert "program" not in rows[0]


def test_admin_updates_status_capacity_and_date(client, create_program, admin_headers):
    program, token = create_program(capacity=5)
    response = client.patch(
        f"/api/admin/programs/{program['slug']}", headers=admin_headers, json={"capacity": 9, "start_date": _day(20), "status": "draft"}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["capacity"], body["start_date"], body["status"]) == (9, _day(20), "draft")
    assert client.get("/api/programs", params={"q": token}).json()["items"] == []
    assert client.patch("/api/admin/programs/no-such-programme", headers=admin_headers, json={"capacity": 3}).status_code == 404


def test_programme_create_validation(client, admin_headers):
    base = {
        "title": "Family planning talk",
        "program_type": "education",
        "organizer_name": "Clinic",
        "venue": "Hall",
        "town": "Thika",
        "county": "Kiambu",
        "start_date": _day(5),
        "start_time": "10:00",
        "end_time": "12:00",
        "capacity": 10,
    }
    for change in ({"capacity": 0}, {"program_type": "surgery"}, {"cost_type": "donation"}, {"title": "abc"}):
        assert client.post("/api/admin/programs", headers=admin_headers, json={**base, **change}).status_code == 422
    assert client.patch("/api/admin/programs/anything", headers=admin_headers, json={"capacity": 0}).status_code == 422


def test_admin_programme_endpoints_are_admin_only(client, create_program, make_user, make_facility):
    program, _ = create_program()
    slug = program["slug"]
    calls = [
        ("get", "/api/admin/programs", None),
        ("post", "/api/admin/programs", {}),
        ("patch", f"/api/admin/programs/{slug}", {"capacity": 2}),
        ("get", f"/api/admin/programs/{slug}/registrations", None),
    ]
    patient = make_user()[1]
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    for method, url, body in calls:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url
        assert getattr(client, method)(url, headers=patient, **kwargs).status_code == 403, url
        assert getattr(client, method)(url, headers=staff, **kwargs).status_code == 403, url


def test_my_registrations_is_for_patients_only(client, make_user, make_facility):
    assert client.get("/api/me/registrations").status_code == 401
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    assert client.get("/api/me/registrations", headers=staff).status_code == 403
