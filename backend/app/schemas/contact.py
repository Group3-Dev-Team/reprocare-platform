"""Request body for the Contact Us form."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

ContactTopic = Literal["general", "listing_correction", "privacy", "technical", "feedback"]


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    topic: ContactTopic = "general"
    message: str = Field(min_length=10, max_length=4000)
    website: str = Field(default="", max_length=200, description="Honeypot: must stay empty")


class ContactStatusUpdate(BaseModel):
    status: Literal["new", "in_progress", "resolved"]
