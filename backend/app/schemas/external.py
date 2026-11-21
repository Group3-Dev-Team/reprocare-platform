"""Request bodies for external public feedback imports (bot)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["facebook", "tiktok", "google"]


class ExternalCommentIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    parent_external_id: str | None = Field(default=None, max_length=255)
    author_name: str = Field(default="", max_length=255)
    author_is_facility: bool = False
    text: str = Field(max_length=10000)
    published_at: datetime | None = None
    published_at_approximate: bool = False
    collected_at: datetime | None = None
    like_count: int | None = Field(default=None, ge=0)
    source_rating: int | None = Field(default=None, ge=1, le=5)  # Google reviews only


class ExternalPostIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=10, max_length=2000)
    author_name: str = Field(default="", max_length=255)
    caption: str = Field(default="", max_length=10000)
    thumbnail_url: str = Field(default="", max_length=2000)
    published_at: datetime | None = None
    collected_at: datetime | None = None
    match_method: str = Field(default="manual", max_length=40)


class ExternalBatchIn(BaseModel):
    """One post/video/listing and its comments, for exactly one facility identified without guesswork."""

    platform: Platform
    facility_slug: str | None = Field(default=None, max_length=120)
    google_place_id: str | None = Field(default=None, max_length=255)
    post: ExternalPostIn
    comments: list[ExternalCommentIn] = Field(default_factory=list, max_length=2000)


class ExternalImportRequest(BaseModel):
    batches: list[ExternalBatchIn] = Field(min_length=1, max_length=200)
