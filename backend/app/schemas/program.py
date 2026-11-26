"""Request bodies for community programmes and registrations."""

import re
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.phone import normalise_kenyan

# A programme date further ahead than this is almost certainly a typing mistake (for example 2062 for 2026).
MAX_DAYS_AHEAD = 730
# Accepts the administrator form's "9:00 am" / "1:00 pm" as well as 24-hour "09:00".
_TIME = re.compile(r"^(\d{1,2}):([0-5]\d)\s*([ap]\.?m\.?)?$", re.IGNORECASE)


def time_in_minutes(value: str) -> int:
    """Minutes after midnight for a programme time, or ValueError if it is not a time."""
    match = _TIME.match(value.strip())
    if not match:
        raise ValueError("Use a time such as 09:00 or 9:00 am.")
    hour, minute, suffix = int(match.group(1)), int(match.group(2)), match.group(3)
    if suffix:
        if not 1 <= hour <= 12:
            raise ValueError("Use a time such as 09:00 or 9:00 am.")
        hour = hour % 12 + (12 if suffix.lower().startswith("p") else 0)
    elif hour > 23:
        raise ValueError("Use a time such as 09:00 or 9:00 am.")
    return hour * 60 + minute


def _not_too_far_ahead(value: date | None) -> date | None:
    if value is not None and value > date.today() + timedelta(days=MAX_DAYS_AHEAD):
        raise ValueError("The programme date is more than two years away. Check the year.")
    return value


class RegistrationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    consent: bool

    _check_phone = field_validator("phone")(normalise_kenyan)


class ProgramCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    program_type: Literal["screening", "testing", "education", "outreach"]
    summary: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=4000)
    organizer_name: str = Field(min_length=2, max_length=160)
    service_slug: str | None = None
    venue: str = Field(min_length=2, max_length=255)
    town: str = Field(min_length=2, max_length=80)
    county: str = Field(min_length=2, max_length=80)
    latitude: float | None = None
    longitude: float | None = None
    start_date: date
    start_time: str = Field(min_length=3, max_length=20)
    end_time: str = Field(min_length=3, max_length=20)
    eligibility: str = Field(default="", max_length=1000)
    requirements: str = Field(default="", max_length=1000)
    cost_type: Literal["free", "subsidised", "paid"] = "free"
    cost_note: str = Field(default="", max_length=255)
    capacity: int = Field(gt=0, le=10000)
    status: Literal["published", "draft", "cancelled"] = "published"

    _check_date = field_validator("start_date")(_not_too_far_ahead)

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        time_in_minutes(value)
        return value.strip()

    @model_validator(mode="after")
    def times_and_location(self):
        if time_in_minutes(self.end_time) <= time_in_minutes(self.start_time):
            raise ValueError("The end time must be after the start time.")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Give both latitude and longitude, or neither.")
        # Same bounding box as the facility import contract (Kenya).
        if self.latitude is not None and not (-5.0 <= self.latitude <= 5.5 and 33.5 <= self.longitude <= 42.5):
            raise ValueError("The location must be in Kenya.")
        return self


class ProgramUpdate(BaseModel):
    status: Literal["published", "draft", "cancelled"] | None = None
    capacity: int | None = Field(default=None, gt=0, le=10000)
    start_date: date | None = None

    _check_date = field_validator("start_date")(_not_too_far_ahead)


class RegistrationStatusUpdate(BaseModel):
    """Administrators record attendance; "registered" undoes an attendance mark made by mistake."""

    status: Literal["attended", "registered"]
