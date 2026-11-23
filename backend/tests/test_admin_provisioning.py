import secrets
import warnings
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.database import provision_admin
from app.database.session import SessionLocal
from app.main import app
from app.models import User


# Branch-local fixtures: built with the shared factories so these tests run on main without the
# authentication workstream's routes. The HTTP sign-in checks run once /api/auth/login is registered.
def _has_route(path):
    return path in app.openapi()["paths"]


@pytest.fixture()
def new_patient(make_user):
    user, headers = make_user()
    return headers, {"id": user.id, "email": user.email, "full_name": user.full_name}


@pytest.fixture()
def staff_headers(make_user, make_facility):
    return make_user(role="facility_staff", facility=make_facility())[1]


def test_provisioned_admin_lifecycle(client, new_patient, staff_headers, monkeypatch, capsys):
    email = "local-provisioning-admin@example.com"
    password = "9a" + secrets.token_urlsafe(24)
    monkeypatch.setattr(provision_admin.settings, "environment", "development")
    # The test session can use a scratch Unix socket while the CLI validates a TCP loopback target.
    monkeypatch.setattr(provision_admin, "engine", SimpleNamespace(url=make_url("postgresql+psycopg://localhost/reprocare_test")))
    monkeypatch.setattr(provision_admin.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    answers = iter([email.upper(), " Local Admin ", email, "Unchanged Admin"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    entered = iter([password, password, password + "new", password + "new"])
    monkeypatch.setattr(provision_admin.getpass, "getpass", lambda _: next(entered))

    provision_admin.main([])
    provision_admin.main([])
    output = capsys.readouterr().out
    assert "Administrator created." in output
    assert "An active administrator already uses that email." in output
    assert password not in output

    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        assert user.full_name == "Local Admin"
        assert user.role == "admin" and user.is_active
        assert user.facility_id is None
        assert user.password_hash != password

    if not _has_route("/api/auth/login"):
        return  # sign-in and admin-route checks need the authentication workstream (integration test)
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    body = login.json()
    assert body["user"]["role"] == "admin"
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.get("/api/admin/overview", headers=headers).status_code == 200
    assert client.get("/api/admin/users", headers=headers).status_code == 200
    patient_headers, _ = new_patient
    for denied in (patient_headers, staff_headers):
        assert client.get("/api/admin/users", headers=denied).status_code == 403
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/admin/users", headers=headers).status_code == 401


def test_existing_patient_is_preserved(new_patient):
    _, patient = new_patient
    with SessionLocal() as db:
        original = db.get(User, patient["id"])
        original_hash = original.password_hash
        with pytest.raises(provision_admin.ProvisioningError, match="Existing accounts are left unchanged"):
            provision_admin.provision_admin(
                db, email=patient["email"].upper(), full_name="Wrong Name", password="9a" + secrets.token_urlsafe(24)
            )

    with SessionLocal() as db:
        user = db.get(User, patient["id"])
        assert user.role == "patient"
        assert user.full_name == patient["full_name"]
        assert user.password_hash == original_hash


@pytest.mark.parametrize("environment,database_url", [
    ("production", "postgresql+psycopg://localhost/reprocare"),
    ("development", "postgresql+psycopg://db.example.com/reprocare"),
    ("development", "postgresql+psycopg://localhost/reprocare?hostaddr=192.0.2.10"),
])
def test_other_targets_are_rejected_before_prompt(environment, database_url, monkeypatch):
    monkeypatch.setattr(provision_admin.settings, "environment", environment)
    monkeypatch.setattr(provision_admin, "engine", SimpleNamespace(url=make_url(database_url)))
    with pytest.raises(SystemExit, match="requires a loopback PostgreSQL database"):
        provision_admin.main([])


def test_refuses_password_prompt_fallback(monkeypatch):
    monkeypatch.setattr(provision_admin.settings, "environment", "development")
    monkeypatch.setattr(provision_admin, "engine", SimpleNamespace(url=make_url("postgresql+psycopg://localhost/reprocare_test")))
    monkeypatch.setattr(provision_admin.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    answers = iter(["local-provisioning-admin@example.com", "Local Admin"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    def no_secure_terminal(_):
        warnings.warn("Unable to control terminal echo", provision_admin.getpass.GetPassWarning)

    monkeypatch.setattr(provision_admin.getpass, "getpass", no_secure_terminal)
    with pytest.raises(SystemExit, match="could not securely read the password"):
        provision_admin.main([])
