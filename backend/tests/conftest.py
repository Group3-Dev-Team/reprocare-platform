"""Test setup shared by every workstream.

Tests run against a dedicated disposable PostgreSQL database (TEST_DATABASE_URL). The session-wide `database`
fixture rebuilds its tables once and loads the reference catalogue; the guard in app/database/test_safety.py
refuses any database that is not clearly a test database.

Factory fixtures create the records a test needs, so feature tests do not depend on another workstream's
endpoints (for example the sign-in routes) or on demo seed data.
"""

import itertools
import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://reprocare:reprocare@localhost:5432/reprocare_test")
os.environ["APP_ENV"] = "test"
os.environ.setdefault("IMPORT_API_KEY", "test-import-key")

import pytest  # noqa: E402
from sqlalchemy import MetaData  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.init_db import create_tables  # noqa: E402
from app.database.seed_reference import load_reference  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.database.test_safety import assert_disposable_database  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Facility, Service, User  # noqa: E402
from app.services.auth_service import create_session, hash_password  # noqa: E402

_counter = itertools.count(1)


@pytest.fixture(scope="session", autouse=True)
def database():
    assert_disposable_database(os.environ["DATABASE_URL"])
    # Drop every table present, including ones created by other workstreams' models, then rebuild.
    existing = MetaData()
    existing.reflect(bind=engine)
    existing.drop_all(bind=engine)
    create_tables(reset=True)
    with SessionLocal() as db:
        load_reference(db)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def make_facility():
    """Create a facility. Pass `services=["antenatal", ...]` to link catalogue services."""

    def factory(services=(), **fields):
        n = next(_counter)
        values = {
            "slug": f"test-facility-{n}",
            "name": f"Test Facility {n}",
            "facility_type": "clinic",
            "town": "Nairobi",
            "county": "Nairobi",
            "accepts_appointment_requests": True,
            "is_demo": True,
        }
        values.update(fields)
        with SessionLocal() as db:
            facility = Facility(**values)
            if services:
                facility.services = list(db.query(Service).filter(Service.slug.in_(services)))
            db.add(facility)
            db.commit()
            db.refresh(facility)
            return facility

    return factory


@pytest.fixture()
def make_user():
    """Create a user and return (user, auth headers). Roles: patient, facility_staff (needs facility), admin."""

    def factory(role="patient", facility=None, password="Secret123", **fields):
        n = next(_counter)
        with SessionLocal() as db:
            user = User(
                email=fields.pop("email", f"user{n}@example.com"),
                full_name=fields.pop("full_name", f"Test User {n}"),
                password_hash=hash_password(password),
                role=role,
                facility_id=facility.id if facility is not None else None,
                phone=fields.pop("phone", "+254700000000"),
                **fields,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_session(db, user)
            db.commit()
            return user, {"Authorization": f"Bearer {token}"}

    return factory
