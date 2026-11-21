"""Loopback-only display of already collected Facebook activity."""

from collections import defaultdict
from ipaddress import ip_address
import re
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import ExternalPost, Facility, FacilityExternalProfile
from app.routes.external_feedback_routes import comment_page, post_page
from app.services.external_feedback_service import PLATFORM_HOSTS, visible_comment_counts

router = APIRouter(prefix="/local-demo", tags=["Local demo"])
DEMO_COMMENT_STATUSES = ("visible", "held")

# Public page identities checked against the stored post paths and facility profiles.
# Shared accounts are shown in the organizations view, irrespective of collection branch.
FACILITY_PAGES = {
    "africa-inuka-hospital": "africainukahospital",
    "aic-litein-hospital": "liteinhospitalaic",
    "bayleaf-hospital": "bayleafhospital",
    "embu-level-5-hospital": "embulevel5hosp",
    "guardian-hospital-meru": "guardianhospitalmeru",
    "kilimani-hospital": "kilimanihosp",
    "kisumu-specialist-hospital": "kisumuspecialistshospital",
    "mephi-hospital": "mephihospitalkilifi",
    "meru-jordan-hospital-ltd": "merujordan",
    "p-c-e-a-t-m-t-m-hospital": "pceatumutumuhospital",
    "premier-hospital": "premierhospke",
    "st-brigittas-hospital": "stbrigittashospital",
    "star-specialist-hospital": "starhospitalmalindi",
    "the-aga-khan-hospital-kisumu": "akhkisumu",
    "valley-hospital": "valleyhospitalltdnakuru",
}
ORGANIZATIONS = {
    "aarhealthcareofficial": "AAR Healthcare",
    "africamissionservices": "Africa Mission Services",
    "akuhnairobi": "Aga Khan University Hospital, Nairobi",
    "avenuehealthcarekenya": "Avenue Healthcare",
    "marie.stopes.kenya.1985": "Marie Stopes Kenya",
    "nairobiwomenshospital": "The Nairobi Women’s Hospital",
    "nrhstoday": "Nyanza Reproductive Health Society",
    "officialradianthospitals": "Radiant Group of Hospitals",
    "rfhhealthcare": "RFH Healthcare",
    "tkh2006": "The Karen Hospital",
}


def _loopback(host):
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def require_local_demo(request: Request, response: Response):
    origin = request.headers.get("origin")
    try:
        origin_host = urlsplit(origin).hostname if origin else None
    except ValueError:
        raise HTTPException(404, "Local Facebook demo is unavailable.") from None
    if (
        not settings.local_facebook_demo
        or settings.environment != "development"
        or not request.client
        or not _loopback(request.client.host)
        or not _loopback(request.url.hostname)
        or (origin and not _loopback(origin_host))
    ):
        raise HTTPException(404, "Local Facebook demo is unavailable.")
    response.headers["Cache-Control"] = "no-store"


def _page(url, *, post=False):
    try:
        source = urlsplit(url or "")
    except ValueError:
        return ""
    if source.scheme != "https" or source.hostname not in PLATFORM_HOSTS["facebook"] or source.username or source.password:
        return ""
    parts = source.path.strip("/").casefold().split("/")
    if post and (len(parts) != 3 or parts[1] != "posts" or not parts[2]):
        return ""
    if not post and len(parts) != 1:
        return ""
    key = parts[0]
    return key if re.fullmatch(r"[a-z0-9._-]+", key) and key not in {"groups", "people", "brand", "share"} else ""


# These branch names independently identify the same organization. A stored
# profile match alone is insufficient (a similarly named listing is linked).
def _facility_organizations(db, slug):
    if not slug or not slug.startswith("marie-stopes-"):
        return []
    urls = db.scalars(
        select(FacilityExternalProfile.url)
        .join(Facility, Facility.id == FacilityExternalProfile.facility_id)
        .where(Facility.slug == slug, FacilityExternalProfile.platform == "facebook")
    )
    key = "marie.stopes.kenya.1985"
    return [{"key": key, "name": ORGANIZATIONS[key]}] if any(_page(url) == key for url in urls) else []


def _collection(db):
    profiles = defaultdict(set)
    page_facilities = defaultdict(set)
    for facility_id, url in db.execute(select(FacilityExternalProfile.facility_id, FacilityExternalProfile.url)
                                      .where(FacilityExternalProfile.platform == "facebook")):
        key = _page(url)
        if key:
            profiles[facility_id].add(key)
            page_facilities[key].add(facility_id)
    posts = db.execute(select(ExternalPost.id, ExternalPost.url, ExternalPost.facility_id, Facility.slug)
                       .outerjoin(Facility, Facility.id == ExternalPost.facility_id)
                       .where(ExternalPost.platform == "facebook")).all()
    result = {}
    for post_id, url, facility_id, slug in posts:
        key = _page(url, post=True)
        if not key or key == "wix":
            scope = "excluded"
        elif key not in profiles[facility_id]:
            scope = "unattributed"
        elif key in ORGANIZATIONS:
            scope = "organization"
        elif FACILITY_PAGES.get(slug) == key and page_facilities[key] == {facility_id}:
            scope = "facility"
        else:
            scope = "unattributed"
        result[post_id] = (scope, key, slug)
    return result


def _shape(post, entry):
    scope, key, _ = entry
    post.update(attribution_scope=scope, author=post["author"] or ORGANIZATIONS.get(key) or f"@{key}",
                page_name=ORGANIZATIONS.get(key) or f"@{key}", page_url=f"https://www.facebook.com/{key}")
    return post


@router.get("/facebook/posts", dependencies=[Depends(require_local_demo)])
def list_demo_posts(
    scope: Literal["facility", "organization", "unattributed"],
    slug: str | None = None,
    organization: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=20),
    db: Session = Depends(get_db),
):
    if scope == "facility" and not slug:
        raise HTTPException(422, "A facility is required.")
    collection = _collection(db)
    ids = [pid for pid, (group, key, linked_slug) in collection.items()
           if group == scope and (scope != "facility" or slug == linked_slug)
           and (scope != "organization" or organization is None or organization == key)]
    query = (select(ExternalPost).where(ExternalPost.id.in_(ids))
             .order_by(ExternalPost.collected_at.desc().nulls_last(), ExternalPost.id.desc()))
    result = post_page(db, query, page, page_size, 3, DEMO_COMMENT_STATUSES)
    result["items"] = [_shape(post, collection[post["id"]]) for post in result["items"]]
    result["comment_total"] = sum(visible_comment_counts(db, ids, DEMO_COMMENT_STATUSES).values())
    if scope == "facility":
        result["related_organizations"] = _facility_organizations(db, slug)
    result["organizations"] = [{"key": key, "name": ORGANIZATIONS[key]}
                               for key in sorted({key for group, key, _ in collection.values() if group == "organization"},
                                                 key=ORGANIZATIONS.get)]
    return result


@router.get("/facebook/counts", dependencies=[Depends(require_local_demo)])
def demo_counts(db: Session = Depends(get_db)):
    collection = _collection(db)
    counts = visible_comment_counts(db, list(collection), DEMO_COMMENT_STATUSES)
    totals = {group: {"posts": 0, "comments": 0} for group in ("facility", "organization", "unattributed", "excluded")}
    for pid, (group, _, _) in collection.items():
        totals[group]["posts"] += 1
        totals[group]["comments"] += counts.get(pid, 0)
    return totals


@router.get("/facebook/facilities", dependencies=[Depends(require_local_demo)])
def demo_facilities(db: Session = Depends(get_db)):
    post_totals = defaultdict(int)
    for scope, _, slug in _collection(db).values():
        if scope == "facility":
            post_totals[slug] += 1
    rows = db.execute(
        select(Facility.slug, Facility.name)
        .where(Facility.slug.in_(post_totals))
        .order_by(Facility.name, Facility.slug)
    )
    return [{"slug": slug, "name": name, "posts": post_totals[slug]} for slug, name in rows]


@router.get("/facebook/posts/{post_id}/comments", dependencies=[Depends(require_local_demo)])
def demo_comments(post_id: int, page: int = Query(1, ge=1), page_size: int = Query(8, ge=1, le=40),
                  db: Session = Depends(get_db)):
    entry = _collection(db).get(post_id)
    if not entry or entry[0] == "excluded":
        raise HTTPException(404, "That post is unavailable in the demo.")
    result = comment_page(db, db.get(ExternalPost, post_id), page, page_size, DEMO_COMMENT_STATUSES)
    _shape(result["post"], entry)
    return result


@router.get("/instagram/{slug}", dependencies=[Depends(require_local_demo)])
def instagram_demo_posts(slug: str):
    from app.services.instagram_capture import load_facility_capture

    try:
        return {"items": load_facility_capture(slug)}
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, "The authorized Instagram capture could not be loaded.") from None
