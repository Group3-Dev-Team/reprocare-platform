"""The JSON contract the external data bot (or an administrator) uses to import facilities.

Full description and an example: docs/DATA_IMPORT_CONTRACT.md and backend/tests/sample_import.json.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


class ImportRequest(BaseModel):
    source: ImportSource
    # True for test fixtures. Their records are flagged as demonstration data and never mixed with genuine listings.
    is_demo: bool = False
    facilities: list[dict] = Field(min_length=1, max_length=500)
