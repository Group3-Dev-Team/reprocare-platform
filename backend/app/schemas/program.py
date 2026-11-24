"""Request bodies for community programmes and registrations."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RegistrationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    consent: bool


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


class ProgramUpdate(BaseModel):
    status: Literal["published", "draft", "cancelled"] | None = None
    capacity: int | None = Field(default=None, gt=0, le=10000)
    start_date: date | None = None
