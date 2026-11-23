"""External public feedback (SYSTEM 2): read-only public pages and the bot import endpoint.

Nothing here feeds the ReproCare rating. Explicit Google and public-feedback filters
use separate source data (see services/facility_service.py).
"""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import ExternalCollectionRun, ExternalComment, ExternalPost, Facility, FacilityExternalProfile, User
from app.schemas.external import ExternalImportRequest
from app.services.auth_service import get_optional_user
from app.services.common import paginate
from app.services.external_feedback_service import (
    PLATFORM_LABELS,
    comment_to_dict,
    import_batches,
    post_to_dict,
    published_external_post,
    viewable_comment,
    visible_comment_counts,
)

router = APIRouter(tags=["External public feedback"])

NOTICE = (
    "Public comments collected from Facebook, TikTok and Google. They are shown for information only, "
    "are not ReproCare reviews, and do not affect any ReproCare rating or ranking."
)


def _facility(db: Session, slug: str) -> Facility:
    facility = db.scalar(select(Facility).where(Facility.slug == slug))
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    return facility


def _visible_comment():
    return (ExternalComment.post_id == ExternalPost.id) & viewable_comment()


# --------------------------------------------------------------------------- public

@router.get("/facilities/{slug}/public-feedback")
def public_feedback_summary(slug: str, db: Session = Depends(get_db)):
    facility = _facility(db, slug)

    google = db.scalar(
        select(FacilityExternalProfile)
        .where(FacilityExternalProfile.facility_id == facility.id, FacilityExternalProfile.platform == "google",
               FacilityExternalProfile.rating.between(1, 5))
        .order_by(FacilityExternalProfile.fetched_at.desc().nulls_last())
    )
    rows = db.execute(
        select(
            ExternalPost.platform,
            func.count(func.distinct(ExternalPost.id)),
            func.count(ExternalComment.id),
            func.max(ExternalComment.collected_at),
        )
        .join(ExternalComment, _visible_comment())
        .where(ExternalPost.facility_id == facility.id, published_external_post())
        .group_by(ExternalPost.platform)
    ).all()
    by_platform = {p: {"posts": posts, "comments": comments, "last_collected_at": last.isoformat() if last else None} for p, posts, comments, last in rows}
    platforms = [
        {"platform": p, "label": PLATFORM_LABELS[p], **by_platform.get(p, {"posts": 0, "comments": 0, "last_collected_at": None})}
        for p in ("facebook", "tiktok", "google")
    ]
    profiles = db.scalars(select(FacilityExternalProfile).where(FacilityExternalProfile.facility_id == facility.id)).all()
    last_runs = {
        platform: {"status": run_status, "message": message, "at": at.isoformat() if at else None}
        for platform, run_status, message, at in db.execute(
            select(ExternalCollectionRun.platform, ExternalCollectionRun.status, ExternalCollectionRun.message, ExternalCollectionRun.started_at)
            .where(ExternalCollectionRun.facility_id == facility.id)
            .order_by(ExternalCollectionRun.started_at.asc())
        ).all()
    }
    return {
        "notice": NOTICE,
        "total_comments": sum(p["comments"] for p in platforms),
        "platforms": platforms,
        "google": {
            "rating": google.rating,
            "rating_count": google.rating_count,
            "url": google.url,
            "place_id": google.external_id,
            "photo_count": len(google.photos or []),
            "fetched_at": google.fetched_at.isoformat() if google.fetched_at else None,
            "attribution": "Rating from Google Maps users. Not a ReproCare rating.",
        }
        if google and google.rating is not None
        else None,
        "accounts": [
            {"platform": p.platform, "label": PLATFORM_LABELS[p.platform], "url": p.url, "name": p.display_name, "match_method": p.match_method}
            for p in profiles
            if p.url and p.platform != "facebook"
        ],
        "last_runs": last_runs,
    }


@router.get("/facilities/{slug}/public-feedback/posts")
def public_feedback_posts(
    slug: str,
    platform: str | None = Query(None, pattern="^(facebook|tiktok|google)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=20),
    preview: int = Query(3, ge=0, le=10),
    db: Session = Depends(get_db),
):
    """Posts/videos/listings that have at least one visible comment, newest first, each with a short preview."""
    facility = _facility(db, slug)
    query = (
        select(ExternalPost)
        .where(ExternalPost.facility_id == facility.id, published_external_post(), exists().where(_visible_comment()))
        .order_by(ExternalPost.published_at.desc().nulls_last(), ExternalPost.collected_at.desc().nulls_last(), ExternalPost.id.desc())
    )
    if platform:
        query = query.where(ExternalPost.platform == platform)
    return post_page(db, query, page, page_size, preview)


def post_page(db, query, page, page_size, preview, statuses=("visible",)):
    result = paginate(db, query, page, page_size, lambda p: p)
    posts = result["items"]
    counts = visible_comment_counts(db, [p.id for p in posts], statuses)
    items = []
    for p in posts:
        first = []
        if preview:
            first = db.scalars(
                select(ExternalComment)
                .where(ExternalComment.post_id == p.id, ExternalComment.status.in_(statuses), ExternalComment.parent_id.is_(None))
                .order_by(ExternalComment.like_count.desc().nulls_last(), ExternalComment.published_at.desc().nulls_last(), ExternalComment.id)
                .limit(preview)
            ).all()
        items.append(post_to_dict(p, counts.get(p.id, 0), [comment_to_dict(c) for c in first]))
    result["items"] = items
    return result


@router.get("/external-posts/{post_id}/comments")
def external_post_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=40),
    db: Session = Depends(get_db),
):
    """Top-level visible comments of one post, with their visible replies nested."""
    post = db.scalar(select(ExternalPost).where(ExternalPost.id == post_id, published_external_post(), ExternalPost.facility_id.is_not(None)))
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That post is not available.")
    return comment_page(db, post, page, page_size)


def comment_page(db, post, page, page_size, statuses=("visible",)):
    query = (
        select(ExternalComment)
        .where(ExternalComment.post_id == post.id, ExternalComment.status.in_(statuses), ExternalComment.parent_id.is_(None))
        .order_by(ExternalComment.like_count.desc().nulls_last(), ExternalComment.published_at.desc().nulls_last(), ExternalComment.id)
    )
    result = paginate(db, query, page, page_size, lambda c: c)
    parent_ids = [c.id for c in result["items"]]
    replies: dict[int, list] = {}
    if parent_ids:
        for r in db.scalars(
            select(ExternalComment)
            .where(ExternalComment.post_id == post.id, ExternalComment.parent_id.in_(parent_ids), ExternalComment.status.in_(statuses))
            .order_by(ExternalComment.published_at.asc().nulls_last(), ExternalComment.id)
        ):
            replies.setdefault(r.parent_id, []).append(r)
    result["items"] = [comment_to_dict(c, replies.get(c.id, [])) for c in result["items"]]
    result["post"] = post_to_dict(post, visible_comment_counts(db, [post.id], statuses).get(post.id, 0))
    return result


# --------------------------------------------------------------------------- bot import

@router.post("/import/external-feedback")
def import_external_feedback(
    body: ExternalImportRequest,
    x_import_key: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Same authentication as /import/facilities: the bot's X-Import-Key or an administrator session."""
    key_ok = bool(settings.import_api_key) and x_import_key is not None and hmac.compare_digest(x_import_key, settings.import_api_key)
    if not (key_ok or (user is not None and user.role == "admin")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid import key or an administrator session is required.")
    result = import_batches(db, body.batches)
    result.pop("results", None)
    return result
