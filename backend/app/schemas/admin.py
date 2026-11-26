"""Request bodies used only by platform administrators and facility staff."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import _password_rules
from app.services.phone import check_facility_numbers


class StaffAccountCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)

    role: Literal["facility_staff", "admin"]
    facility_slug: str | None = None

    _check_password = field_validator("password")(_password_rules)


class UserStatusUpdate(BaseModel):
    is_active: bool


class FacilityProfileUpdate(BaseModel):

    description: str = Field(default="", max_length=2000)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=255)

    _check_phone = field_validator("phone")(check_facility_numbers)
    website: str = Field(default="", max_length=255)
    weekday_hours: str = Field(default="", max_length=60)
    saturday_hours: str = Field(default="", max_length=60)
    sunday_hours: str = Field(default="", max_length=60)
    accepts_appointment_requests: bool = False

