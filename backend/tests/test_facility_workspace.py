"""Facility workspace: staff see their own facility's overview and maintain its public profile."""

from datetime import date, timedelta


def _future(days=10):
    return (date.today() + timedelta(days=days)).isoformat()


def test_overview_counts_own_facility_only(client, make_facility, make_user):
    facility = make_facility(services=["antenatal"])
    other = make_facility(services=["antenatal"])
    _, staff = make_user(role="facility_staff", facility=facility)
    _, patient = make_user()
    for target, day in ((facility, 10), (facility, 11), (other, 12)):
        response = client.post("/api/appointments", headers=patient, json={
            "facility_slug": target.slug, "preferred_date": _future(day), "preferred_time": "morning", "contact_phone": "+254711000333",
        })
        assert response.status_code == 201, response.text

    overview = client.get("/api/facility/overview", headers=staff)
    assert overview.status_code == 200
    body = overview.json()
    assert body["facility"]["slug"] == facility.slug
    assert body["appointments"]["requested"] == 2
    assert body["appointments"]["confirmed"] == 0
    assert body["reviews_awaiting_reply"] == 0


def test_profile_update_and_weekend_flag(client, make_facility, make_user):
    facility = make_facility()
    _, staff = make_user(role="facility_staff", facility=facility)
    update = {
        "description": "  Maternity and family planning.  ", "phone": "+254700111222", "email": "", "website": "",
        "weekday_hours": "08:00-17:00", "saturday_hours": "09:00-13:00", "sunday_hours": "Closed",
        "accepts_appointment_requests": True, "offers_telehealth": False,
    }
    response = client.patch("/api/facility/profile", headers=staff, json=update)
    assert response.status_code == 200, response.text
    assert response.json()["slug"] == facility.slug

    overview = client.get("/api/facility/overview", headers=staff).json()["facility"]
    assert overview["description"] == "Maternity and family planning."

    closed = {**update, "saturday_hours": "closed", "sunday_hours": ""}
    assert client.patch("/api/facility/profile", headers=staff, json=closed).status_code == 200
    from app.database.session import SessionLocal
    from app.models import Facility

    with SessionLocal() as db:
        assert db.get(Facility, facility.id).open_weekends is False


def test_workspace_is_for_facility_staff_only(client, make_user):
    _, patient = make_user()
    _, admin = make_user(role="admin")
    assert client.get("/api/facility/overview").status_code == 401
    assert client.get("/api/facility/overview", headers=patient).status_code == 403
    assert client.get("/api/facility/overview", headers=admin).status_code == 403
    assert client.patch("/api/facility/profile", headers=patient, json={}).status_code == 403
