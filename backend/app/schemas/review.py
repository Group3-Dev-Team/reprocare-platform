"""Request bodies for patient experiences (reviews)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=4, max_length=160)
    body: str = Field(min_length=20, max_length=3000)
    service_slug: str | None = Field(default=None, max_length=60)
    visit_month: date | None = None
    consent: bool = Field(description="The author agrees to publish the text after moderation.")


class ReviewModeration(BaseModel):
    decision: Literal["published", "rejected"]
    note: str = Field(default="", max_length=500)


class ReviewReply(BaseModel):
    reply: str = Field(min_length=2, max_length=1500)
