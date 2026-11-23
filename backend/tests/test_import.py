"""The data-ingestion contract used by the independent bot."""

import json
from pathlib import Path

SAMPLE = json.loads((Path(__file__).parent / "sample_import.json").read_text())
KEY = {"X-Import-Key": "test-import-key"}


def test_import_creates_then_updates_and_is_retrievable(client):
    first = client.post("/api/import/facilities", headers=KEY, json=SAMPLE)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["created"] == 2 and result["failed"] == 1  # the sample has one deliberately invalid record
    assert result["errors"][0]["index"] == 2

    slug = result["records"][0]["slug"]
    detail = client.get(f"/api/facilities/{slug}").json()
    assert detail["name"] == SAMPLE["facilities"][0]["name"]
    assert detail["source"]["code"] == "reprocare_bot_test" and detail["is_demo"] is True
    assert {s["slug"] for s in detail["services"]} == set(SAMPLE["facilities"][0]["services"])

    # Same external IDs again: records are updated, not duplicated
    changed = json.loads(json.dumps(SAMPLE))
    changed["facilities"][0]["phone"] = "+254700999888"
    second = client.post("/api/import/facilities", headers=KEY, json=changed).json()
    assert second["created"] == 0 and second["updated"] == 2
    assert client.get(f"/api/facilities/{slug}").json()["phone"] == "+254700999888"

    # Imported record is searchable through the normal API
    found = client.get("/api/facilities", params={"q": SAMPLE["facilities"][0]["name"]}).json()
    assert any(f["slug"] == slug for f in found["items"])


def test_unknown_service_codes_are_reported(client):
    payload = {"source": {"code": "reprocare_bot_test"}, "is_demo": True, "facilities": [
        {"external_id": "bad-svc", "name": "Test Clinic", "facility_type": "clinic", "town": "Nakuru", "county": "Nakuru", "services": ["teleportation"]}
    ]}
    r = client.post("/api/import/facilities", headers=KEY, json=payload).json()
    assert r["failed"] == 1 and "teleportation" in r["errors"][0]["error"]


def test_admin_can_import_and_see_history(client, admin_headers):
    payload = {"source": {"code": "admin_upload_test"}, "is_demo": True, "facilities": [
        {"external_id": "adm-1", "name": "Admin Test Health Centre", "facility_type": "health_centre", "town": "Nyeri", "county": "Nyeri"}
    ]}
    assert client.post("/api/import/facilities", headers=admin_headers, json=payload).json()["created"] == 1
    history = client.get("/api/admin/imports", headers=admin_headers).json()
    assert history and history[0]["source"] == "admin_upload_test"


def test_demo_source_is_reserved(client):
    payload = {"source": {"code": "demo"}, "facilities": [{"external_id": "1"}]}
    assert client.post("/api/import/facilities", headers=KEY, json=payload).status_code == 400


def test_reimport_without_services_keeps_existing_links(client):
    base = {"external_id": "keep-links-1", "name": "Link Keeper Clinic", "facility_type": "clinic", "town": "Thika", "county": "Kiambu"}
    payload = {"source": {"code": "reprocare_bot_test"}, "is_demo": True, "facilities": [{**base, "services": ["antenatal", "lab"], "insurers": ["sha"]}]}
    slug = client.post("/api/import/facilities", headers=KEY, json=payload).json()["records"][0]["slug"]

    # a location-only refresh omits services and insurers: links stay
    refresh = {**payload, "facilities": [{**base, "phone": "+254700111222"}]}
    assert client.post("/api/import/facilities", headers=KEY, json=refresh).json()["updated"] == 1
    detail = client.get(f"/api/facilities/{slug}").json()
    assert {s["slug"] for s in detail["services"]} == {"antenatal", "lab"}
    assert {i["slug"] for i in detail["insurers"]} == {"sha"}

    # an explicit empty list still clears them
    clear = {**payload, "facilities": [{**base, "services": [], "insurers": []}]}
    client.post("/api/import/facilities", headers=KEY, json=clear)
    detail = client.get(f"/api/facilities/{slug}").json()
    assert detail["services"] == [] and detail["insurers"] == []
