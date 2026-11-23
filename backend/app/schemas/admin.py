"""Request bodies used only by platform administrators and facility staff."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import _password_rules


class StaffAccountCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)
    # only these two roles can be created by an admin, patients sign up themselves
    role: Literal["facility_staff", "admin"]
    facility_slug: str | None = None

    _check_password = field_validator("password")(_password_rules)


class UserStatusUpdate(BaseModel):
    is_active: bool


class FacilityProfileUpdate(BaseModel):
    # what clinic staff can change on their own facility, registration details stay locked
    description: str = Field(default="", max_length=2000)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=255)
    website: str = Field(default="", max_length=255)
    weekday_hours: str = Field(default="", max_length=60)
    saturday_hours: str = Field(default="", max_length=60)
    sunday_hours: str = Field(default="", max_length=60)
    accepts_appointment_requests: bool = False
    offers_telehealth: bool = False