"""Read-only Facebook collection on local development facility pages."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import ExternalComment, ExternalPost, Facility, FacilityExternalProfile
from app.routes.facebook_demo_routes import FACILITY_PAGES, ORGANIZATIONS, _loopback, _page
from app.services.external_feedback_service import comment_to_dict, post_to_dict, published_external_post
from app.services.feedback_screening import EMAIL, PHONE, UNRELATED_PHRASES, screen_feedback

router = APIRouter(prefix="/local-collection/facebook", tags=["Local Facebook collection"])
Scope = Literal["facility", "organization"]

# A stored page link alone can be wrong or point to the parent organization.
ORGANIZATION_BRANCHES = {
    "aarhealthcareofficial": ("aar-healthcare",),
    "akuhnairobi": ("aga-khan", "the-aga-khan"),
    "avenuehealthcarekenya": ("avenue-healthcare",),
    "marie.stopes.kenya.1985": ("marie-stopes",),
    "nairobiwomenshospital": ("the-nairobi-women", "nairobi-women"),
    "nrhstoday": ("nyanza-reproductive-health",),
    "officialradianthospitals": ("radiant",),
    "rfhhealthcare": ("rfh",),
    "tkh2006": ("the-karen-hospital", "karen-hospital"),
}
LOGISTICS = re.compile(
    r"\b(?:appointments?|book(?:ing)?|branches?|charges?|costs?|hours|locations?|prices?|"
    r"opening hours|how much|where (?:are|is|can|do)|which branch)\b", re.I
)
SENSITIVE = re.compile(
    r"\b(?:hiv|stds?|stis?|diagnos(?:ed|is)|(?:lab|test) results?|medical records?|"
    r"patient (?:id|number)|id number|identity card|my (?:pregnancy|abortion|miscarriage)|"
    r"i (?:am|was) pregnant)\b", re.I
)
SPACED_PHONE = re.compile(r"(?<!\d)(?:\+254|0)[ .-]*[17](?:[ .-]*\d){8}(?!\d)")
SAFE_CONTEXT = {"general_comment", "hospital_match_only"}
ELIGIBLE_REASONS = SAFE_CONTEXT | {"hospital_and_service_match", "service_related"}


def require_local_collection(request: Request, response: Response):
    try:
        origin = request.headers.get("origin")
        origin_is_local = not origin or _loopback(urlsplit(origin).hostname)
        forwarded_client = request.headers.get("x-forwarded-for")
        forwarded_is_local = not forwarded_client or all(_loopback(host.strip()) for host in forwarded_client.split(","))
        forwarded_host = request.headers.get("x-forwarded-host")
        host_is_local = not forwarded_host or _loopback(urlsplit("//" + forwarded_host).hostname)
    except ValueError:
        origin_is_local = forwarded_is_local = host_is_local = False
    if (
        settings.environment != "development"
        or request.client is None
        or not _loopback(request.client.host)
        or not _loopback(request.url.hostname)
        or not origin_is_local
        or not forwarded_is_local
        or not host_is_local
        or request.headers.get("forwarded")
    ):
        raise HTTPException(404, "Local Facebook collection is unavailable.")
    response.headers["Cache-Control"] = "no-store"


@dataclass(frozen=True)
class PageEvidence:
    key: str
    scope: Scope
    facility_name: str


def _name_key(name: str) -> str:
    return re.sub(r"[\W_]", "", name.strip().casefold().removesuffix(" | facebook"))


def _page_evidence(db: Session) -> dict[tuple[int, str], PageEvidence]:
    rows = db.execute(
        select(Facility.id, Facility.slug, Facility.name, Facility.website, FacilityExternalProfile)
        .join(FacilityExternalProfile, FacilityExternalProfile.facility_id == Facility.id)
        .where(FacilityExternalProfile.platform == "facebook", Facility.is_demo.is_(False))
    ).all()
    owners = defaultdict(set)
    profiles = []
    for facility_id, slug, name, website, profile in rows:
        if key := _page(profile.url):
            owners[key].add(facility_id)
            if website and key != "wix" and profile.match_method == "official_website":
                profiles.append((facility_id, slug, name, profile.display_name, key))

    evidence = {}
    for facility_id, slug, name, display_name, key in profiles:
        if key in ORGANIZATIONS:
            if any(slug == prefix or slug.startswith(prefix + "-") for prefix in ORGANIZATION_BRANCHES.get(key, ())):
                evidence[facility_id, key] = PageEvidence(key, "organization", name)
        elif owners[key] == {facility_id} and (
            FACILITY_PAGES.get(slug) == key or _name_key(name) in {_name_key(key), _name_key(display_name or "")}
        ):
            evidence[facility_id, key] = PageEvidence(key, "facility", name)
    return evidence


def _safe_text(text: str) -> bool:
    return bool(text.strip()) and not (
        PHONE.search(text) or SPACED_PHONE.search(text) or EMAIL.search(text) or SENSITIVE.search(text)
        or any(phrase in text.casefold() for phrase in UNRELATED_PHRASES)
    )


def _threads(post: ExternalPost, evidence: PageEvidence, comments: list[ExternalComment]) -> list[dict]:
    eligible, facility_replies = set(), set()
    for comment in comments:
        if not _safe_text(comment.text) or not set(comment.screening_reasons or ()) <= ELIGIBLE_REASONS:
            continue
        result = screen_feedback(evidence.facility_name, comment.text, post.caption or "")
        if result.status == "candidate" or (set(result.reasons) <= SAFE_CONTEXT and LOGISTICS.search(comment.text)):
            eligible.add(comment.id)
        elif comment.author_is_facility and set(result.reasons) <= SAFE_CONTEXT:
            facility_replies.add(comment.id)

    replies = defaultdict(list)
    roots = {comment.id for comment in comments if comment.parent_id is None and comment.id in eligible}
    eligible_replies = eligible | facility_replies
    for comment in comments:
        if comment.parent_id in roots and comment.id in eligible_replies:
            replies[comment.parent_id].append(comment)
    return [comment_to_dict(comment, replies[comment.id]) for comment in comments if comment.id in roots]


@dataclass
class CollectedPost:
    post: ExternalPost
    evidence: PageEvidence
    threads: list[dict]

    @property
    def comment_count(self) -> int:
        return sum(1 + len(thread["replies"]) for thread in self.threads)

    @property
    def caption(self) -> str:
        text = self.post.caption or ""
        if _safe_text(text) and set(screen_feedback("", text).reasons) <= ELIGIBLE_REASONS:
            return text
        return ""

    def shape(self, preview=0) -> dict:
        value = post_to_dict(self.post, self.comment_count)
        # Media from an unreviewed collection may contain information text screening cannot detect.
        value["thumbnail_url"] = ""
        value["caption"] = self.caption
        value["preview"] = [{**thread, "replies": []} for thread in self.threads[:preview]]
        value["attribution_scope"] = self.evidence.scope
        value["page_name"] = ORGANIZATIONS.get(self.evidence.key) or f"@{self.evidence.key}"
        value["author"] = value["page_name"]
        value["page_url"] = f"https://www.facebook.com/{self.evidence.key}"
        value["display_status"] = "collected"
        return value


def _collection(db: Session, evidence: dict[tuple[int, str], PageEvidence], post_id: int | None = None) -> list[CollectedPost]:
    query = select(ExternalPost).where(
        ExternalPost.platform == "facebook",
        ExternalPost.match_method == "facility_page_post",
        ExternalPost.facebook_reviewed_at.is_(None),
        ~published_external_post(),
        ExternalPost.facility_id.in_({facility_id for facility_id, _ in evidence}),
    ).order_by(ExternalPost.published_at.desc().nulls_last(), ExternalPost.collected_at.desc().nulls_last(), ExternalPost.id.desc())
    if post_id is not None:
        query = query.where(ExternalPost.id == post_id)
    posts = [
        (post, match) for post in db.scalars(query)
        if (match := evidence.get((post.facility_id, _page(post.url, post=True))))
    ]
    if not posts:
        return []
    comments = defaultdict(list)
    for comment in db.scalars(
        select(ExternalComment).where(
            ExternalComment.post_id.in_([post.id for post, _ in posts]),
            ExternalComment.platform == "facebook",
            ExternalComment.status.in_(("visible", "held")),
        ).order_by(ExternalComment.id)
    ):
        comments[comment.post_id].append(comment)
    return [
        CollectedPost(post, match, threads)
        for post, match in posts if (threads := _threads(post, match, comments[post.id]))
    ]


def _page_result(items: list, page: int, page_size: int) -> dict:
    total = len(items)
    return {
        "items": items[(page - 1) * page_size : page * page_size],
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


def _feedback_totals(posts: list[CollectedPost]) -> dict:
    comments = sum(post.comment_count for post in posts)
    return {"comment_total": comments, "written_total": comments + sum(bool(post.caption) for post in posts)}


@router.get("/facilities/{slug}/posts", dependencies=[Depends(require_local_collection)])
def collected_posts(
    slug: str,
    scope: Scope = "facility",
    organization: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=20),
    db: Session = Depends(get_db),
):
    facility_id = db.scalar(select(Facility.id).where(Facility.slug == slug))
    if facility_id is None:
        raise HTTPException(404, "We could not find that facility.")
    evidence = _page_evidence(db)
    org_keys = {entry.key for (fid, _), entry in evidence.items() if fid == facility_id and entry.scope == "organization"}
    relevant = {
        identity: entry for identity, entry in evidence.items()
        if (entry.scope == "facility" and identity[0] == facility_id)
        or (entry.scope == "organization" and entry.key in org_keys)
    }
    collection = _collection(db, relevant)
    posts = [
        item for item in collection
        if item.evidence.scope == scope and (organization is None or item.evidence.key == organization)
    ]
    organizations = defaultdict(list)
    if scope == "facility":
        for item in collection:
            if item.evidence.scope == "organization":
                organizations[item.evidence.key].append(item)

    result = _page_result(posts, page, page_size)
    result["items"] = [item.shape(preview=3) for item in result["items"]]
    result.update(_feedback_totals(posts))
    result["related_organizations"] = [
        {"key": key, "name": ORGANIZATIONS[key], "total": len(organizations[key]), **_feedback_totals(organizations[key])}
        for key in sorted(organizations)
    ]
    return result


@router.get("/posts/{post_id}/comments", dependencies=[Depends(require_local_collection)])
def collected_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=40),
    db: Session = Depends(get_db),
):
    posts = _collection(db, _page_evidence(db), post_id)
    if not posts:
        raise HTTPException(404, "That post is not available in the local collection.")
    result = _page_result(posts[0].threads, page, page_size)
    return {**result, "post": posts[0].shape()}
