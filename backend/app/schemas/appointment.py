"""Request bodies for appointment requests."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _within_booking_window(value: date) -> date:
    if value < date.today():
        raise ValueError("Choose today or a later date.")
    if (value - date.today()).days > 180:
        raise ValueError("Choose a date within the next six months.")
    return value


class AppointmentCreate(BaseModel):
    facility_slug: str = Field(min_length=1, max_length=120)
    service_slug: str | None = Field(default=None, max_length=60)
    practitioner_slug: str | None = Field(default=None, max_length=120)
    preferred_date: date
    preferred_time: Literal["morning", "afternoon", "evening"]
    contact_phone: str = Field(min_length=7, max_length=40)
    notes: str = Field(default="", max_length=1000)

    @field_validator("preferred_date")
    @classmethod
    def not_in_past(cls, value: date) -> date:
        return _within_booking_window(value)


class AppointmentReschedule(BaseModel):
    """A patient's proposed new date or time period for an existing request."""

    preferred_date: date
    preferred_time: Literal["morning", "afternoon", "evening"]
    notes: str = Field(default="", max_length=1000)

    @field_validator("preferred_date")
    @classmethod
    def not_in_past(cls, value: date) -> date:
        return _within_booking_window(value)


class AppointmentResponse(BaseModel):
    """A facility's answer to a request."""

    status: Literal["confirmed", "declined"]
    facility_note: str = Field(default="", max_length=1000)
