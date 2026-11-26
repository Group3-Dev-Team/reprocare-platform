"""Phone validation: Kenyan personal numbers are normalised; letters and malformed numbers are refused."""

import pytest

from app.services.phone import check_facility_numbers, normalise_kenyan, optional_kenyan


@pytest.mark.parametrize("raw, expected", [
    ("0712345678", "+254712345678"), ("0712 345 678", "+254712345678"), ("+254 712-345-678", "+254712345678"),
    ("254712345678", "+254712345678"), ("0110 123 456", "+254110123456"), ("020 272 2541", "+254202722541"),
    ("(041) 222 3344", "+254412223344"),
])
def test_valid_kenyan_numbers_are_normalised(raw, expected):
    assert normalise_kenyan(raw) == expected


@pytest.mark.parametrize("raw", ["shgihcwsbdcjebdc", "07123", "071234567890", "+1 202 555 0101", "0712abc678", "", "0012345678", "++254712345678"])
def test_invalid_personal_numbers_are_refused(raw):
    with pytest.raises(ValueError):
        normalise_kenyan(raw)


def test_optional_fields_stay_optional():
    assert optional_kenyan(None) is None and optional_kenyan("  ") is None


@pytest.mark.parametrize("raw", ["020 272 2541", "+254 20 2722541, 0722 123 456", "0800 720 600", "+44 20 7946 0958", ""])
def test_facility_numbers_accept_several_and_international(raw):
    assert check_facility_numbers(raw) == raw.strip()


@pytest.mark.parametrize("raw", ["call reception", "0712 345 678 ext abc", "12"])
def test_facility_numbers_refuse_text(raw):
    with pytest.raises(ValueError):
        check_facility_numbers(raw)


def test_api_refuses_text_phone_on_register(client):
    r = client.post("/api/auth/register", json={"email": "phone-check@example.com", "password": "Valid12345", "full_name": "Phone Check", "phone": "shgihcwsbdcjebdc"})
    assert r.status_code == 422 and r.json()["detail"][0]["loc"][-1] == "phone"
    ok = client.post("/api/auth/register", json={"email": "phone-ok@example.com", "password": "Valid12345", "full_name": "Phone Ok", "phone": "0712 345 678"})
    assert ok.status_code in (200, 201) and ok.json()["user"]["phone"] == "+254712345678"
