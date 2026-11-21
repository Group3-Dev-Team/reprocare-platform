"""External public information collected by the ReproCare bot (SYSTEM 2).

These tables are deliberately separate from `reviews` (SYSTEM 1, ReproCare patient ratings).
The ReproCare rating calculation uses only patient reviews. Explicit Google filters, sorting and
source-labelled comparison read Google snapshots independently.

    facility_external_profiles   one row per facility per platform account (Google place, Facebook page, TikTok search)
                                 Google's own rating / rating count live here, attributed to Google.
    external_posts               a Facebook post, a TikTok video, or a Google listing that holds comments/reviews
    external_comments            one public comment (or reply, or Google review) attached to a post
    external_collection_runs     a log of every bot run: what was attempted, what came back, what failed
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

PLATFORMS = ("facebook", "tiktok", "google")
PLATFORM_CHECK = "platform IN ('facebook', 'tiktok', 'google')"

# How a facility was associated with an external account or post. Never a fuzzy guess.
MATCH_METHODS = (
    "google_place_id",  # Google place id stored on the facility profile
    "official_website",  # link found on the facility's own website
    "public_search_exact",  # single unambiguous public-search result whose title contains the exact facility name
    "facility_page_post",  # post published on the facility's matched Facebook page
    "caption_exact_name",  # TikTok caption contains the facility's full name
    "manual",  # set by an administrator
    "legacy_import",  # migrated from the integration database (external_feedback)
)

# Visibility of an individual comment on patient-facing pages.
COMMENT_STATUSES = ("visible", "held", "hidden")


class FacilityExternalProfile(Base):
    __tablename__ = "facility_external_profiles"
    __table_args__ = (
        CheckConstraint(PLATFORM_CHECK, name="ck_external_profiles_platform"),
        UniqueConstraint("facility_id", "platform", "external_id", name="uq_external_profiles_facility_platform_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str] = mapped_column(String(255))  # Google place id, Facebook page slug, TikTok search key
    url: Mapped[str] = mapped_column(Text, default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")
    match_method: Mapped[str] = mapped_column(String(40), default="manual")
    # Google's own numbers. Shown attributed to Google; NEVER combined with the ReproCare rating.
    rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int | None] = mapped_column(Integer)
    photos: Mapped[list] = mapped_column(JSON, default=list)  # [{"name": "places/…/photos/…", "attributions": [...]}]
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # other fields returned by the source, as returned
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility")


class ExternalPost(Base):
    """The thing people commented on: a Facebook post, a TikTok video, or a Google listing (for Google reviews)."""

    __tablename__ = "external_posts"
    __table_args__ = (
        CheckConstraint(PLATFORM_CHECK, name="ck_external_posts_platform"),
        UniqueConstraint("platform", "external_id", name="uq_external_posts_platform_id"),
        CheckConstraint("facebook_scope IS NULL OR (platform = 'facebook' AND facebook_scope IN ('facility', 'organization'))", name="ck_external_posts_facebook_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"), index=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str] = mapped_column(String(255))  # FB: sha256(url)[:32]; TikTok: video id; Google: place id
    url: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(255), default="")  # page name or creator handle, as published
    caption: Mapped[str] = mapped_column(Text, default="")  # post text / video description, when available
    thumbnail_url: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    match_method: Mapped[str] = mapped_column(String(40), default="manual")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    facebook_scope: Mapped[str | None] = mapped_column(String(20))
    facebook_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    facebook_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    facebook_review_note: Mapped[str | None] = mapped_column(Text)
    # Only for rows migrated from the integration database that could not be linked by id.
    legacy_facility_name: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility")
    comments = relationship("ExternalComment", back_populates="post", cascade="all, delete-orphan")


class ExternalComment(Base):
    __tablename__ = "external_comments"
    __table_args__ = (
        CheckConstraint(PLATFORM_CHECK, name="ck_external_comments_platform"),
        CheckConstraint("status IN ('visible', 'held', 'hidden')", name="ck_external_comments_status"),
        CheckConstraint("source_rating IS NULL OR source_rating BETWEEN 1 AND 5", name="ck_external_comments_rating"),
        UniqueConstraint("platform", "external_id", name="uq_external_comments_platform_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("external_posts.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("external_comments.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str] = mapped_column(String(255))  # TikTok cid, Google review id, FB sha256(post url + text)
    author_name: Mapped[str] = mapped_column(String(255), default="")
    author_is_facility: Mapped[bool] = mapped_column(Boolean, default=False)  # reply posted by the facility's own account
    text: Mapped[str] = mapped_column(Text)
    # Original timestamp from the platform; `published_at_approximate` when derived from "3 weeks ago"-style labels.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at_approximate: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    like_count: Mapped[int | None] = mapped_column(Integer)
    # Google reviews only: the star rating the reviewer gave ON GOOGLE. Displayed with the review, never aggregated by ReproCare.
    source_rating: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="visible", index=True)
    screening: Mapped[str] = mapped_column(String(40), default="")  # candidate | needs_review | irrelevant
    screening_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post = relationship("ExternalPost", back_populates="comments")
    facility = relationship("Facility")
    replies = relationship("ExternalComment", order_by="ExternalComment.id")


class ExternalCollectionRun(Base):
    """One bot step (e.g. 'facebook' for one facility). Lets admins see what ran and why something is empty."""

    __tablename__ = "external_collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"), index=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)  # facebook | tiktok | google | discovery | import
    status: Mapped[str] = mapped_column(String(20))  # succeeded | empty | failed | skipped
    message: Mapped[str] = mapped_column(Text, default="")
    posts_found: Mapped[int] = mapped_column(Integer, default=0)
    comments_created: Mapped[int] = mapped_column(Integer, default=0)
    comments_skipped: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility")
