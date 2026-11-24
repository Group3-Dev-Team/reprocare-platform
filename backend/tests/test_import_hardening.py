"""Facility import hardening (SCRUM-11): duplicate IDs in one batch, record-level database failures,
demonstration/genuine separation and contact-field validation."""

import itertools

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Facility
from app.services import import_service

KEY = {"X-Import-Key": "test-import-key"}
_unique = itertools.count(1)


def _record(external_id, **fields):
    n = next(_unique)
    record = {"external_id": external_id, "name": f"Hardening Clinic {n}", "facility_type": "clinic", "town": "Embu", "county": "Embu"}
    record.update(fields)
    return record


def _import(client, *records, source="hardening_test", is_demo=True):
    response = client.post("/api/import/facilities", headers=KEY, json={"source": {"code": source}, "is_demo": is_demo, "facilities": list(records)})
    assert response.status_code == 200, response.text
    return response.json()


def _stored(source_code, external_id):
    with SessionLocal() as db:
        return db.scalars(
            select(Facility).join(Facility.source).where(Facility.external_id == external_id).where(Facility.source.has(code=source_code))
        ).all()


# --- Duplicate external IDs within one batch -------------------------------------------------------


def test_duplicate_external_ids_in_one_batch_are_all_rejected(client):
    result = _import(client, _record("dup-ok"), _record("dup-x"), _record("dup-x"), source="dup_test")
    assert (result["created"], result["updated"], result["failed"], result["received"]) == (1, 0, 2, 3)
    assert [e["index"] for e in result["errors"]] == [1, 2]
    assert all(e["external_id"] == "dup-x" and "appears 2 times" in e["error"] for e in result["errors"])
    assert [r["external_id"] for r in result["records"]] == ["dup-ok"]
    assert _stored("dup_test", "dup-x") == []


def test_same_external_id_in_separate_batches_still_updates(client):
    first = _import(client, _record("again-1", phone="+254700100100"), source="again_test")
    second = _import(client, _record("again-1", phone="+254700200200"), source="again_test")
    assert (first["created"], second["updated"]) == (1, 1)
    assert second["records"][0]["slug"] == first["records"][0]["slug"]


# --- One database failure does not abort the batch ----------------------------------------------


@pytest.fixture()
def failing_record(monkeypatch):
    """Make the record with external_id 'boom' violate the unique slug constraint when it is flushed."""
    real_apply = import_service._apply

    def apply(facility, record, services, insurers):
        real_apply(facility, record, services, insurers)
        if record.external_id == "boom":
            with SessionLocal() as db:
                facility.slug = db.scalars(select(Facility.slug).where(Facility.slug != facility.slug)).first()

    monkeypatch.setattr(import_service, "_apply", apply)


def test_database_error_fails_only_that_record(client, failing_record, make_user):
    result = _import(client, _record("ok-1"), _record("boom"), _record("ok-2"), source="db_fail_test")
    assert (result["created"], result["failed"]) == (2, 1)
    assert result["errors"][0]["index"] == 1 and result["errors"][0]["external_id"] == "boom"
    assert "database rejected this record" in result["errors"][0]["error"]
    assert [r["external_id"] for r in result["records"]] == ["ok-1", "ok-2"]
    assert len(_stored("db_fail_test", "ok-1")) == 1 and len(_stored("db_fail_test", "ok-2")) == 1
    assert _stored("db_fail_test", "boom") == []

    # the batch is still audited
    admin = make_user(role="admin")[1]
    batch = next(b for b in client.get("/api/admin/imports", headers=admin).json() if b["id"] == result["batch_id"])
    assert (batch["created"], batch["failed"]) == (2, 1)


def test_failed_update_leaves_the_existing_record_unchanged(client, monkeypatch):
    created = _import(client, _record("boom", phone="+254700300300"), source="db_fail_update_test")
    slug = created["records"][0]["slug"]
    real_apply = import_service._apply

    def apply(facility, record, services, insurers):
        real_apply(facility, record, services, insurers)
        with SessionLocal() as db:
            facility.slug = db.scalars(select(Facility.slug).where(Facility.slug != facility.slug)).first()

    monkeypatch.setattr(import_service, "_apply", apply)
    result = _import(client, _record("boom", phone="+254700999999"), source="db_fail_update_test")
    assert (result["updated"], result["failed"]) == (0, 1)
    assert client.get(f"/api/facilities/{slug}").json()["phone"] == "+254700300300"


# --- Demonstration and genuine records -------------------------------------------------------------


def test_genuine_import_cannot_overwrite_demo_record(client):
    slug = _import(client, _record("mix-1", phone="+254700400400"), source="mix_test", is_demo=True)["records"][0]["slug"]
    result = _import(client, _record("mix-1", phone="+254700500500"), source="mix_test", is_demo=False)
    assert (result["created"], result["updated"], result["failed"]) == (0, 0, 1)
    assert "stored as demonstration data" in result["errors"][0]["error"]
    detail = client.get(f"/api/facilities/{slug}").json()
    assert (detail["phone"], detail["is_demo"]) == ("+254700400400", True)


def test_demo_import_cannot_overwrite_genuine_record(client):
    slug = _import(client, _record("mix-2", phone="+254700600600"), source="mix_genuine_test", is_demo=False)["records"][0]["slug"]
    result = _import(client, _record("mix-2", phone="+254700700700"), source="mix_genuine_test", is_demo=True)
    assert result["failed"] == 1 and "stored as genuine data" in result["errors"][0]["error"]
    detail = client.get(f"/api/facilities/{slug}").json()
    assert (detail["phone"], detail["is_demo"]) == ("+254700600600", False)


# --- Contact-field validation -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "field, value",
    [
        ("email", "not-an-email"), ("email", "info@@clinic.example"), ("email", " info@clinic.example"),
        ("phone", "call us"), ("phone", "123 45"), ("phone", "0722-ABC-123"), ("phone", "++254700000000"), ("phone", "0722 000 000 ext 4"),
        ("website", "www.clinic.example"), ("website", "ftp://clinic.example"), ("website", "https://localhost"),
        ("website", "https://clinic .example"), ("website", "clinic.example"),
    ],
)
def test_invalid_contact_fields_fail_the_record_with_a_clear_error(client, field, value):
    result = _import(client, _record("contact-ok"), _record(f"contact-bad-{next(_unique)}", **{field: value}), source="contact_test")
    assert (result["failed"], len(result["records"])) == (1, 1)
    error = result["errors"][0]
    assert error["index"] == 1 and error["error"].startswith(f"{field}:")


@pytest.mark.parametrize(
    "fields",
    [
        {"email": "Info@Clinic.co.ke", "phone": "020 0000000", "website": "https://clinic.example/"},
        {"email": "", "phone": "", "website": ""},
        {"phone": "+254 (0) 722-000-111", "website": "http://www.clinic.example/contact?x=1"},
        {"phone": "0722 000 000 / 0733 000 000"},
    ],
)
def test_valid_contact_fields_are_stored_exactly_as_sent(client, fields):
    result = _import(client, _record(f"contact-good-{next(_unique)}", **fields), source="contact_good_test")
    assert result["failed"] == 0, result["errors"]
    detail = client.get(f"/api/facilities/{result['records'][0]['slug']}").json()
    for field, value in fields.items():
        assert detail[field] == value


# --- Existing behaviour is preserved --------------------------------------------------------------


def test_links_are_kept_when_services_are_omitted_alongside_new_rules(client):
    base = _record("links-1", services=["antenatal"], insurers=["sha"])
    slug = _import(client, base, source="links_test")["records"][0]["slug"]
    refresh = {k: v for k, v in base.items() if k not in ("services", "insurers")}
    result = _import(client, {**refresh, "phone": "+254700800800"}, _record("links-2"), _record("links-2"), source="links_test")
    assert (result["updated"], result["created"], result["failed"]) == (1, 0, 2)
    detail = client.get(f"/api/facilities/{slug}").json()
    assert {s["slug"] for s in detail["services"]} == {"antenatal"}
    assert {i["slug"] for i in detail["insurers"]} == {"sha"}


def test_response_shape_is_unchanged(client):
    result = _import(client, _record("shape-1"), source="shape_test")
    assert set(result) == {"batch_id", "source", "received", "created", "updated", "failed", "errors", "warnings", "records"}
