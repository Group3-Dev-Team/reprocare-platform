"""Admin review of collected Facebook posts and their attribution."""

from datetime import datetime, timezone
from typing import Annotated, Literal
<<<<<<< HEAD
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import ExternalComment, ExternalPost, FacilityExternalProfile, User
=======
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import ExternalComment, ExternalPost, Facility, FacilityExternalProfile, User
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
from app.services.auth_service import require_role
from app.services.common import paginate
from app.services.external_feedback_service import PLATFORM_HOSTS, comment_to_dict, mask_contact_details, valid_source_url

router = APIRouter(prefix="/admin/facebook-feedback", tags=["Administration"])
admin_only = require_role("admin")
Scope = Literal["facility", "organization"]


class FacebookDecision(BaseModel):
    decision: Literal["publish", "withhold"]
    scope: Scope | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    comment_ids: list[int] = Field(default_factory=list)
    reviewed_at: datetime | None


def _page_key(url: str) -> str:
    try:
        source = urlsplit(url)
        if source.hostname in PLATFORM_HOSTS["facebook"]:
<<<<<<< HEAD
            return source.path.strip("/").split("/")[0].casefold()
=======
            segment = source.path.strip("/").split("/")[0].casefold()
            if segment in {"profile.php", "permalink.php", "story.php"}:
                page_id = parse_qs(source.query).get("id", [""])[0]
                return page_id if page_id.isascii() and page_id.isdecimal() else ""
            if segment not in {"photo", "photo.php", "photos", "posts", "reel", "reels", "videos", "watch"}:
                return segment
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
    except ValueError:
        pass
    return ""


def _post_shape(post: ExternalPost) -> dict:
<<<<<<< HEAD
=======
    published = post.is_visible and post.facebook_scope is not None
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
    return {
        "id": post.id,
        "facility": post.facility.name if post.facility else None,
        "source_url": post.url if valid_source_url("facebook", post.url) else None,
<<<<<<< HEAD
        "author": post.author_name,
        "caption": mask_contact_details(post.caption or ""),
        "scope": post.facebook_scope,
        "previously_visible": post.is_visible and post.facebook_scope is None,
        "published": post.is_visible and post.facebook_scope is not None,
=======
        "page": _page_key(post.url) or None,
        "author": post.author_name,
        "caption": mask_contact_details(post.caption or ""),
        "published_at": post.published_at,
        "collected_at": post.collected_at,
        "scope": post.facebook_scope,
        "previously_visible": post.is_visible and post.facebook_scope is None,
        "published": published,
        "status": "published" if published else "withheld" if post.facebook_reviewed_at and not post.is_visible else "pending",
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
        "reviewed_at": post.facebook_reviewed_at,
        "reviewed_by": post.facebook_reviewed_by,
        "note": post.facebook_review_note,
    }


def _facebook_post(post_id: int, db: Session, lock: bool = False) -> ExternalPost:
    query = select(ExternalPost).where(ExternalPost.id == post_id, ExternalPost.platform == "facebook")
    post = db.scalar(query.with_for_update() if lock else query)
    if post is None:
        raise HTTPException(404, "Facebook post not found.")
    return post


@router.get("")
def moderation_queue(
    response: Response,
<<<<<<< HEAD
    status: Literal["pending", "published", "withheld"] = "pending",
    page: int = Query(1, ge=1),
=======
    status: Literal["all", "pending", "published", "withheld"] = "pending",
    page: int = Query(1, ge=1),
    facility_id: int | None = Query(None, ge=1),
    q: str = Query("", max_length=200),
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
<<<<<<< HEAD
    query = select(ExternalPost).where(ExternalPost.platform == "facebook").options(selectinload(ExternalPost.facility))
=======
    query = select(ExternalPost).where(ExternalPost.platform == "facebook")
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
    if status == "pending":
        query = query.where(ExternalPost.facebook_reviewed_at.is_(None))
    elif status == "published":
        query = query.where(ExternalPost.is_visible.is_(True), ExternalPost.facebook_scope.is_not(None))
<<<<<<< HEAD
    else:
        query = query.where(ExternalPost.facebook_reviewed_at.is_not(None), ExternalPost.is_visible.is_(False))
    return paginate(db, query.order_by(ExternalPost.id), page, 20, _post_shape)
=======
    elif status == "withheld":
        query = query.where(ExternalPost.facebook_reviewed_at.is_not(None), ExternalPost.is_visible.is_(False))
    if facility_id is not None:
        query = query.where(ExternalPost.facility_id == facility_id)
    if term := q.strip():
        query = query.outerjoin(Facility, ExternalPost.facility_id == Facility.id).where(or_(
            Facility.name.icontains(term, autoescape=True),
            ExternalPost.author_name.icontains(term, autoescape=True),
            ExternalPost.url.icontains(term, autoescape=True),
            ExternalPost.caption.icontains(term, autoescape=True),
        ))

    result = paginate(db, query.options(selectinload(ExternalPost.facility)).order_by(ExternalPost.id), page, 20, lambda post: post)
    posts = result["items"]
    counts = dict(db.execute(
        select(ExternalComment.post_id, func.count(ExternalComment.id))
        .where(ExternalComment.post_id.in_([post.id for post in posts]))
        .group_by(ExternalComment.post_id)
    ).all()) if posts else {}
    result["items"] = [{**_post_shape(post), "comment_count": counts.get(post.id, 0)} for post in posts]
    result["comment_total"] = db.scalar(select(func.count(ExternalComment.id)).where(
        ExternalComment.post_id.in_(query.with_only_columns(ExternalPost.id))
    ))
    result["facilities"] = [
        {"id": facility_id, "name": name}
        for facility_id, name in db.execute(
            select(Facility.id, Facility.name).join(ExternalPost, ExternalPost.facility_id == Facility.id)
            .where(ExternalPost.platform == "facebook").distinct().order_by(Facility.name, Facility.id)
        )
    ]
    return result
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68


@router.get("/{post_id}")
def moderation_detail(post_id: int, response: Response, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    post = _facebook_post(post_id, db)
    profiles = db.scalars(
        select(FacilityExternalProfile)
        .where(FacilityExternalProfile.platform == "facebook")
        .options(selectinload(FacilityExternalProfile.facility))
        .order_by(FacilityExternalProfile.id)
    ).all()
    page = _page_key(post.url)
    comments = db.scalars(
        select(ExternalComment).where(ExternalComment.post_id == post.id).order_by(ExternalComment.id)
    ).all()
    return {
        **_post_shape(post),
<<<<<<< HEAD
=======
        "comment_count": len(comments),
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
        "profiles": [
            {"facility": p.facility.name, "linked_facility": p.facility_id == post.facility_id,
             "page": _page_key(p.url), "page_matches": bool(page) and _page_key(p.url) == page,
             "name": p.display_name, "match_method": p.match_method}
            for p in profiles if p.facility_id == post.facility_id or (page and _page_key(p.url) == page)
        ],
        "comments": [
            {**comment_to_dict(c), "parent_id": c.parent_id, "status": c.status,
             "screening": c.screening, "screening_reasons": c.screening_reasons}
            for c in comments
        ],
    }


@router.post("/{post_id}/moderate")
def moderate_facebook_post(
    post_id: int, body: FacebookDecision, user: User = Depends(admin_only), db: Session = Depends(get_db),
):
    post = _facebook_post(post_id, db, lock=True)
    if body.reviewed_at != post.facebook_reviewed_at:
        raise HTTPException(409, "This decision has changed. Reload the post before reviewing.")
    if body.decision == "publish":
        if body.scope is None or post.facility_id is None or not valid_source_url("facebook", post.url):
            raise HTTPException(422, "Publication requires an attribution scope, a linked facility and a valid Facebook source.")
        comments = db.scalars(select(ExternalComment).where(ExternalComment.post_id == post.id)).all()
        selectable = {c.id: c for c in comments if c.status != "hidden"}
        selected = set(body.comment_ids)
        if not selected or not selected <= selectable.keys():
            raise HTTPException(422, "Select at least one eligible comment from this post.")
        for cid in selected:
            parent_id = selectable[cid].parent_id
            if parent_id is not None and (parent_id not in selected or selectable[parent_id].parent_id is not None):
                raise HTTPException(422, "Select the visible top-level parent of each reply.")
        for cid, comment in selectable.items():
            comment.status = "visible" if cid in selected else "held"
        post.facebook_scope = body.scope
    else:
        post.facebook_scope = None
    post.is_visible = body.decision == "publish"
    post.facebook_reviewed_at = datetime.now(timezone.utc)
    post.facebook_reviewed_by = user.id
    post.facebook_review_note = body.note
    result = _post_shape(post)
    db.commit()
    return result
