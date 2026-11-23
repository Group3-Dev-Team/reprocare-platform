"""Foundation checks: the API starts, the schema builds and shared auth helpers work."""

import pytest
from fastapi import Depends

from app.database.session import SessionLocal
from app.database.test_safety import assert_disposable_database
from app.main import app
from app.models import DataSource, Service
from app.services.auth_service import require_role


@app.get("/api/_test/admin-only")
def _admin_only(user=Depends(require_role("admin"))):
    return {"email": user.email}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_schema_and_reference_catalogue():
    with SessionLocal() as db:
        assert db.query(Service).count() == 11
        assert db.query(DataSource).filter_by(code="google_places").count() == 1


def test_factories_and_role_checks(client, make_facility, make_user):
    facility = make_facility(services=["antenatal"])
    with SessionLocal() as db:
        from app.models import Facility

        assert [s.slug for s in db.get(Facility, facility.id).services] == ["antenatal"]
    _, patient = make_user()
    _, admin = make_user(role="admin")
    _, staff = make_user(role="facility_staff", facility=facility)
    assert client.get("/api/_test/admin-only").status_code == 401
    assert client.get("/api/_test/admin-only", headers=patient).status_code == 403
    assert client.get("/api/_test/admin-only", headers=staff).status_code == 403
    assert client.get("/api/_test/admin-only", headers=admin).status_code == 200


def test_guard_refuses_non_test_database():
    with pytest.raises(RuntimeError):
        assert_disposable_database("postgresql+psycopg://u:p@localhost:5432/reprocare")
    assert_disposable_database("postgresql+psycopg://u:p@localhost:5432/reprocare_test")
