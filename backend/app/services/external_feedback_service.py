"""Store and read external public feedback (SYSTEM 2). Used by the bot, the import API and the public pages.

Rules enforced here, in one place:
* every post is tied to exactly one facility, resolved by slug or Google place id — never by fuzzy name matching;
* a post already attributed to one facility is never silently moved to another;
* re-running an import never duplicates a post or a comment (unique platform + external id);
* source URLs must belong to the platform they claim to come from;
* text is stored exactly as collected; phone numbers and emails are masked when shown to visitors.
"""

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import ExternalCollectionRun, ExternalComment, ExternalPost, Facility, FacilityExternalProfile
from app.schemas.external import ExternalBatchIn
from app.services.feedback_screening import EMAIL, PHONE, screen_feedback

PLATFORM_HOSTS = {
    "facebook": {"facebook.com", "www.facebook.com", "web.facebook.com", "m.facebook.com"},
    "tiktok": {"tiktok.com", "www.tiktok.com"},
    "google": {"google.com", "www.google.com", "maps.google.com", "maps.app.goo.gl", "goo.gl"},
}
FACEBOOK_POST_MARKERS = ("/posts/", "/videos/", "/photos/", "/permalink", "/reel/")

PLATFORM_LABELS = {"facebook": "Facebook", "tiktok": "TikTok", "google": "Google"}


class ImportRejected(ValueError):
    pass


def valid_source_url(platform: str, url: str) -> bool:
    try:
        parsed = urlparse(url or "")
        hostname = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme != "https" or hostname not in PLATFORM_HOSTS.get(platform, set()) or parsed.username is not None or parsed.password is not None:
        return False
    if platform == "facebook":
        return any(marker in parsed.path for marker in FACEBOOK_POST_MARKERS) or "story_fbid" in parse_qs(parsed.query)
    if platform == "tiktok":
        return "/video/" in parsed.path
    return True


def _now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_facility(db: Session, facility_slug: str | None, google_place_id: str | None) -> Facility:
    """Exact identifiers only. A name is not enough to attribute public feedback."""
    if facility_slug:
        facility = db.scalar(select(Facility).where(Facility.slug == facility_slug))
        if facility:
            return facility
        raise ImportRejected(f"No facility with slug '{facility_slug}'.")
    if google_place_id:
        facility = db.scalar(
            select(Facility)
            .join(FacilityExternalProfile, FacilityExternalProfile.facility_id == Facility.id)
            .where(FacilityExternalProfile.platform == "google", FacilityExternalProfile.external_id == google_place_id)
        )
        if facility is None:  # facilities imported by the legacy importer stored the place id in facilities.external_id
            facility = db.scalar(select(Facility).where(Facility.external_id == google_place_id))
        if facility:
            return facility
        raise ImportRejected("No facility is linked to that Google place id.")
    raise ImportRejected("A facility slug or Google place id is required.")


def upsert_profile(db: Session, facility: Facility, platform: str, external_id: str, **fields) -> FacilityExternalProfile:
    profile = db.scalar(
        select(FacilityExternalProfile).where(
            FacilityExternalProfile.facility_id == facility.id,
            FacilityExternalProfile.platform == platform,
            FacilityExternalProfile.external_id == external_id,
        )
    )
    if profile is None:
        profile = FacilityExternalProfile(facility_id=facility.id, platform=platform, external_id=external_id)
        db.add(profile)
    for key, value in fields.items():
        if value is not None:
            setattr(profile, key, value)
    profile.fetched_at = fields.get("fetched_at") or _now()
    db.flush()
    return profile


def record_run(db: Session, platform: str, status: str, message: str = "", facility: Facility | None = None, **counts) -> ExternalCollectionRun:
    run = ExternalCollectionRun(facility_id=facility.id if facility else None, platform=platform, status=status, message=message[:2000], **counts)
    db.add(run)
    db.flush()
    return run


def import_batch(db: Session, batch: ExternalBatchIn) -> dict:
    """Store one post and its comments. Returns counts; raises ImportRejected (nothing stored for this batch)."""
    facility = resolve_facility(db, batch.facility_slug, batch.google_place_id)
    if not valid_source_url(batch.platform, batch.post.url):
        raise ImportRejected(f"The post URL is not a valid {PLATFORM_LABELS[batch.platform]} link.")

    query = select(ExternalPost).where(ExternalPost.platform == batch.platform, ExternalPost.external_id == batch.post.external_id)
    post = db.scalar(query.with_for_update() if batch.platform == "facebook" else query)
    post_created = False
    if post is None:
        post = ExternalPost(
            facility_id=facility.id,
            platform=batch.platform,
            external_id=batch.post.external_id,
            url=batch.post.url,
            match_method=batch.post.match_method,
            is_visible=batch.platform != "facebook",
        )
        db.add(post)
        post_created = True
    elif post.facility_id not in (None, facility.id):
        raise ImportRejected("This post is already attributed to a different facility; it was not moved.")
    elif post.facility_id is None:
        post.facility_id = facility.id

    # Fill in context that later runs may have and earlier runs did not; never blank out existing values.
    if post.facebook_scope is None:
        for attr in ("author_name", "caption", "thumbnail_url", "published_at"):
            value = getattr(batch.post, attr)
            if value and not getattr(post, attr):
                setattr(post, attr, value)
    post.collected_at = batch.post.collected_at or post.collected_at or _now()
    db.flush()

    existing = {
        ext_id: cid
        for ext_id, cid in db.execute(
            select(ExternalComment.external_id, ExternalComment.id).where(
                ExternalComment.platform == batch.platform,
                ExternalComment.external_id.in_([c.external_id for c in batch.comments] or [""]),
            )
        ).all()
    }
    created = skipped = empty = 0
    by_external_id: dict[str, ExternalComment] = {}
    # Top-level comments first so replies can point at their parent.
    ordered = sorted(batch.comments, key=lambda c: c.parent_external_id is not None)
    for item in ordered:
        if item.external_id in existing or item.external_id in by_external_id:
            skipped += 1
            continue
        text = item.text.strip()
        if not text:
            empty += 1
            continue
        parent_id = None
        if item.parent_external_id:
            parent = by_external_id.get(item.parent_external_id)
            parent_id = parent.id if parent else existing.get(item.parent_external_id)
            if parent_id is None:
                parent_id = db.scalar(
                    select(ExternalComment.id).where(ExternalComment.platform == batch.platform, ExternalComment.external_id == item.parent_external_id)
                )
        if item.author_is_facility:
            screening_status, reasons = "facility_reply", []
        else:
            result = screen_feedback(facility.name, text, batch.post.caption)
            screening_status, reasons = result.status, result.reasons
        comment = ExternalComment(
            post_id=post.id,
            facility_id=facility.id,
            parent_id=parent_id,
            platform=batch.platform,
            external_id=item.external_id,
            author_name=item.author_name.strip(),
            author_is_facility=item.author_is_facility,
            text=item.text,  # exactly as collected
            published_at=item.published_at,
            published_at_approximate=item.published_at_approximate,
            collected_at=item.collected_at or batch.post.collected_at or _now(),
            like_count=item.like_count,
            source_rating=item.source_rating if batch.platform == "google" else None,
            status="held" if batch.platform == "facebook" else "visible",
            screening=screening_status,
            screening_reasons=reasons,
        )
        db.add(comment)
        db.flush()
        by_external_id[item.external_id] = comment
        created += 1

    return {
        "facility": facility.slug,
        "post_id": post.id,
        "post_created": post_created,
        "comments_created": created,
        "comments_skipped": skipped,
        "comments_empty": empty,
    }


def import_batches(db: Session, batches: list[ExternalBatchIn]) -> dict:
    """Each batch commits independently, so one bad post never blocks the rest."""
    results, errors = [], []
    for index, batch in enumerate(batches):
        try:
            results.append(import_batch(db, batch))
            db.commit()
        except ImportRejected as exc:
            db.rollback()
            errors.append({"index": index, "external_id": batch.post.external_id, "error": str(exc)})
    return {
        "received": len(batches),
        "imported": len(results),
        "comments_created": sum(r["comments_created"] for r in results),
        "comments_skipped": sum(r["comments_skipped"] for r in results),
        "errors": errors,
        "results": results,
    }


# --------------------------------------------------------------------------- reading (public pages)

def display_author(name: str, is_facility: bool) -> str:
    """Patient-facing author label. Facility accounts by name; people as 'First L.' (data minimisation)."""
    name = " ".join((name or "").split())
    if not name:
        return "Public user"
    if is_facility:
        return name
    parts = name.split(" ")
    if len(parts) == 1:
        return parts[0][:40]
    return f"{parts[0][:30]} {parts[-1][0].upper()}."


def mask_contact_details(text: str) -> str:
    """Data minimisation on display: hide phone numbers and email addresses that people posted publicly."""
    text = PHONE.sub("[phone number hidden]", text)
    return EMAIL.sub("[email hidden]", text)


def comment_to_dict(c: ExternalComment, replies: list[ExternalComment] | None = None) -> dict:
    return {
        "id": c.id,
        "platform": c.platform,
        "platform_label": PLATFORM_LABELS[c.platform],
        "author": display_author(c.author_name, c.author_is_facility),
        "author_is_facility": c.author_is_facility,
        "text": mask_contact_details(c.text),
        "published_at": c.published_at.isoformat() if c.published_at else None,
        "published_at_approximate": c.published_at_approximate,
        "collected_at": c.collected_at.isoformat() if c.collected_at else None,
        "like_count": c.like_count,
        "source_rating": c.source_rating,
        "replies": [comment_to_dict(r) for r in (replies or [])],
    }


def post_to_dict(p: ExternalPost, comment_count: int = 0, preview: list[dict] | None = None) -> dict:
    return {
        "id": p.id,
        "platform": p.platform,
        "platform_label": PLATFORM_LABELS[p.platform],
        "url": p.url,
        "author": p.author_name,
        "caption": mask_contact_details(p.caption or "") if p.platform == "facebook" else p.caption,
        "thumbnail_url": p.thumbnail_url,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "collected_at": p.collected_at.isoformat() if p.collected_at else None,
        "match_method": p.match_method,
        "attribution_scope": p.facebook_scope,
        "comment_count": comment_count,
        "preview": preview or [],
    }


def published_external_post():
    """Match the public feedback routes; local demo visibility is handled separately."""
    return ExternalPost.is_visible.is_(True) & or_(
        ExternalPost.platform != "facebook", ExternalPost.facebook_scope.is_not(None)
    )


def viewable_comment(statuses=("visible",)):
    """Match the public thread: visible roots and visible direct replies to those roots."""
    parent = aliased(ExternalComment)
    visible_parent = select(parent.id).where(
        parent.id == ExternalComment.parent_id,
        parent.post_id == ExternalComment.post_id,
        parent.parent_id.is_(None),
        parent.status.in_(statuses),
    ).correlate(ExternalComment).exists()
    return and_(
        ExternalComment.status.in_(statuses),
        or_(ExternalComment.parent_id.is_(None), visible_parent),
    )


def visible_comment_counts(db: Session, post_ids: list[int], statuses=("visible",)) -> dict[int, int]:
    if not post_ids:
        return {}
    rows = db.execute(
        select(ExternalComment.post_id, func.count(ExternalComment.id))
        .where(ExternalComment.post_id.in_(post_ids), viewable_comment(statuses))
        .group_by(ExternalComment.post_id)
    ).all()
    return dict(rows)
