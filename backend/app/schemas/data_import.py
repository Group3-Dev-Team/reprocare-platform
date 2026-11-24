"""The JSON contract the external data bot (or an administrator) uses to import facilities.

Full description and an example: docs/DATA_IMPORT_CONTRACT.md and backend/tests/sample_import.json.
"""

import re
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator

# Digits, spaces, brackets, hyphens, dots and "/" between numbers; "+" only at the start; at least 7 digits.
_PHONE = re.compile(r"^\+?[0-9 ()./-]+$")

RegistrationStatus = Literal["matched", "not_checked", "unresolved"]
FacilityType = Literal["hospital", "clinic", "maternity_home", "health_centre", "laboratory"]


class ImportSource(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    name: str | None = Field(default=None, max_length=120)
    attribution: str | None = Field(default=None, max_length=255)


class ImportRegistration(BaseModel):
    status: RegistrationStatus = "not_checked"
    body: str = Field(default="", max_length=160)
    code: str = Field(default="", max_length=60)
    checked_on: date | None = None


class ImportFacility(BaseModel):
    external_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=2, max_length=160)
    facility_type: FacilityType
    town: str = Field(min_length=2, max_length=80)
    county: str = Field(min_length=2, max_length=80)
    address: str = Field(default="", max_length=255)
    area: str = Field(default="", max_length=120)
    latitude: float | None = Field(default=None, ge=-5.0, le=5.5)  # Kenya's bounding box
    longitude: float | None = Field(default=None, ge=33.5, le=42.5)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=255)
    website: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=2000)
    weekday_hours: str = Field(default="", max_length=60)
    saturday_hours: str = Field(default="", max_length=60)
    sunday_hours: str = Field(default="", max_length=60)
    open_24_hours: bool = False
    services: list[str] = Field(default_factory=list)  # service slugs, e.g. ["antenatal", "cervical"]
    insurers: list[str] = Field(default_factory=list)  # insurer slugs, e.g. ["sha"]
    registration: ImportRegistration = Field(default_factory=ImportRegistration)

    @field_validator("name", "town", "county")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return " ".join(v.split())

    # Contact fields are checked, never rewritten: an invalid value fails this record with a clear error.
    # An empty string still means "not known".
    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if v:
            try:
                validate_email(v, check_deliverability=False)
            except EmailNotValidError:
                raise ValueError("is not a valid email address") from None
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        if v and not (_PHONE.match(v) and sum(c.isdigit() for c in v) >= 7):
            raise ValueError("is not a valid phone number (digits, spaces, +, -, brackets; at least 7 digits)")
        return v

    @field_validator("website")
    @classmethod
    def valid_website(cls, v: str) -> str:
        if v:
            parts = urlsplit(v)
            if parts.scheme not in {"http", "https"} or "." not in (parts.hostname or "") or any(c.isspace() for c in v):
                raise ValueError("must be a full web address starting with http:// or https://")
        return v


class ImportRequest(BaseModel):
    source: ImportSource
    # True for test fixtures. Their records are flagged as demonstration data and never mixed with genuine listings.
    is_demo: bool = False
    facilities: list[dict] = Field(min_length=1, max_length=500)
