"""Read a private, authorized Instagram capture for the local demo only."""

import json
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.services.external_feedback_service import mask_contact_details

MAX_CAPTURE_BYTES = 2_000_000


class InstagramComment(BaseModel):
    author: str = Field(max_length=120)
    text: str = Field(min_length=1, max_length=3000)


class InstagramPost(BaseModel):
    facility_slug: str = Field(min_length=1, max_length=160)
    account: str = Field(pattern=r"^[A-Za-z0-9._]{1,30}$")
    url: str
    caption: str = Field(default="", max_length=10000)
    captured_at: str
    comments: list[InstagramComment] = Field(default_factory=list, max_length=200)

    @field_validator("url")
    @classmethod
    def post_permalink(cls, value):
        if not re.fullmatch(r"https://(?:www\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?", value):
            raise ValueError("Expected a public Instagram post or reel permalink")
        return value


def load_facility_capture(slug):
    path = os.getenv("REPROCARE_INSTAGRAM_DEMO_CAPTURE")
    if not path:
        return []
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    if len(raw) > MAX_CAPTURE_BYTES:
        raise ValueError("The capture exceeds the local demo limit.")
    items = [InstagramPost.model_validate(item) for item in json.loads(raw)]
    result = []
    for post in items:
        if post.facility_slug == slug:
            row = post.model_dump()
            row["caption"] = mask_contact_details(post.caption)
            for comment in row["comments"]:
                comment["text"] = mask_contact_details(comment["text"])
            result.append(row)
    return result
