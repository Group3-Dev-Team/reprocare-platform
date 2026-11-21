"""Signed facility photo uploads: disabled without configuration, role- and facility-scoped when enabled."""

import hashlib

import pytest

from app.services import media_upload


@pytest.fixture()
def setup(make_facility, make_user):
    facility, other = make_facility(), make_facility()
    _, staff = make_user(role="facility_staff", facility=facility)
    _, patient = make_user()
    _, admin = make_user(role="admin")
    body = {"facility_slug": facility.slug, "content_type": "image/jpeg", "size": 120_000}
    return facility, other, staff, patient, admin, body


def test_disabled_without_configuration(client, setup, monkeypatch):
    facility, other, staff_headers, patient, admin_headers, BODY = setup
    for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        monkeypatch.delenv(name, raising=False)
    assert client.get("/api/media/capabilities").json()["facility_photo_upload"] is False
    assert client.post("/api/media/facility-photo/signature", headers=staff_headers, json=BODY).status_code == 503


def test_signed_parameters_are_scoped_and_validated(client, setup, monkeypatch):
    facility, other, staff_headers, patient, admin_headers, BODY = setup
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "demo-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "key-123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret-xyz")
    assert client.get("/api/media/capabilities").json()["facility_photo_upload"] is True

    assert client.post("/api/media/facility-photo/signature", headers=patient, json=BODY).status_code == 403
    assert client.post("/api/media/facility-photo/signature", headers=staff_headers, json={**BODY, "facility_slug": other.slug}).status_code == 403
    assert client.post("/api/media/facility-photo/signature", headers=staff_headers, json={**BODY, "content_type": "image/gif"}).status_code == 422
    assert client.post("/api/media/facility-photo/signature", headers=staff_headers, json={**BODY, "size": 6 * 1024 * 1024}).status_code == 422

    signed = client.post("/api/media/facility-photo/signature", headers=staff_headers, json=BODY)
    assert signed.status_code == 200
    data = signed.json()
    assert "api_secret" not in data and "secret-xyz" not in signed.text
    assert data["folder"] == f"reprocare/facilities/{facility.slug}"
    expected = "&".join(f"{k}={data[k]}" for k in sorted(("allowed_formats", "folder", "public_id", "timestamp"))) + "secret-xyz"
    assert data["signature"] == hashlib.sha1(expected.encode()).hexdigest()
    assert data["upload_url"] == "https://api.cloudinary.com/v1_1/demo-cloud/image/upload"

    assert client.post("/api/media/facility-photo/signature", headers=admin_headers, json={**BODY, "facility_slug": other.slug}).status_code == 200
    assert client.post("/api/media/facility-photo/signature", headers=admin_headers, json={**BODY, "facility_slug": "missing"}).status_code == 404


def test_signature_matches_cloudinary_rule():
    assert media_upload.sign({"timestamp": 1315060510, "public_id": "sample_image", "eager": ""}, "abcd") == hashlib.sha1(
        b"public_id=sample_image&timestamp=1315060510abcd"
    ).hexdigest()
