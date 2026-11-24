"""Facility search, filtering, sorting and the JSON shapes the frontend receives."""

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ExternalComment, ExternalPost, Facility, FacilityExternalProfile, Insurer, Review, Service,
    facility_insurers, facility_services,
)
from app.services.common import split_list
from app.services.county_service import county_filter_labels
from app.services.external_feedback_service import published_external_post, viewable_comment

FACILITY_TYPE_LABELS = {
    "hospital": "Hospital",
    "clinic": "Clinic",
    "maternity_home": "Maternity home",
    "health_centre": "Health centre",
    "laboratory": "Laboratory",
}


def rating_subquery():
    """Average rating and count of *published ReproCare* reviews, per facility."""
    return (
        select(
            Review.facility_id.label("facility_id"),
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .where(Review.status == "published")
        .group_by(Review.facility_id)
        .subquery()
    )


def distance_km_expression(lat: float, lng: float):
    """Great-circle distance in kilometres, computed by PostgreSQL."""
    return 6371 * func.acos(
        func.least(
            1.0,
            func.cos(func.radians(lat))
            * func.cos(func.radians(Facility.latitude))
            * func.cos(func.radians(Facility.longitude) - func.radians(lng))
            + func.sin(func.radians(lat)) * func.sin(func.radians(Facility.latitude)),
        )
    )


def matching_service_ids(db: Session, text: str) -> list[int]:
    """Services whose name or search keywords contain the text, e.g. 'mimba' -> Antenatal care."""
    like = f"%{text.lower()}%"
    return list(db.scalars(select(Service.id).where(or_(func.lower(Service.name).like(like), func.lower(Service.keywords).like(like)))))


def latest_google_snapshot():
    """Use the same most recent valid rating as the facility card."""
    profile = FacilityExternalProfile
    return (
        select(profile.facility_id, profile.rating, profile.rating_count)
        .where(profile.platform == "google", profile.rating.between(1, 5))
        .ext(distinct_on(profile.facility_id))
        .order_by(profile.facility_id, profile.fetched_at.desc().nulls_last(), profile.id.desc())
        .subquery()
    )


# Kenya keeps East Africa Time (UTC+3) all year, so a fixed offset needs no time zone database.
KENYA_TIME = timezone(timedelta(hours=3))
# Stored opening hours look like "8:00 AM – 5:00 PM" (Google Places), "8:00 – 11:30 AM", "08:00-17:00",
# "Open 24 hours" or "Closed".
_HOURS_RANGE = re.compile(r"^(\d{1,2}):(\d{2})\s*(?:([ap])\.?m\.?)?\s*[-–—]\s*(\d{1,2}):(\d{2})\s*(?:([ap])\.?m\.?)?$", re.IGNORECASE)


def _minute_of_day(hour: str, minute: str, period: str | None) -> int | None:
    hour, minute = int(hour), int(minute)
    if minute > 59 or (period and not 1 <= hour <= 12) or (not period and hour > 23):
        return None
    if period:
        hour = hour % 12 + (12 if period.lower() == "p" else 0)
    return hour * 60 + minute


def _opening_range(hours: str):
    """(start, end) in minutes for a readable range, True for "Open 24 hours", False for "Closed", None when unreadable."""
    text = " ".join((hours or "").replace("\u202f", " ").replace("\u2009", " ").replace("\xa0", " ").split())
    if text.lower() in ("open 24 hours", "24 hours"):
        return True
    if text.lower() == "closed":
        return False
    match = _HOURS_RANGE.match(text)
    if not match:
        return None
    first_period, second_period = match.group(3), match.group(6)
    if first_period and not second_period:
        return None
    start = _minute_of_day(match.group(1), match.group(2), first_period or second_period)  # "8:00 – 11:30 AM"
    end = _minute_of_day(match.group(4), match.group(5), second_period)
    if start is None or end is None or start == end:
        return None
    return start, end


def open_at(hours: str, minute: int, previous_hours: str = "") -> bool | None:
    """Whether stored opening hours say the facility is open at this minute of the day; None when they cannot be read.
    The early-morning part of an overnight range ("6:00 PM – 2:00 AM") belongs to the next day, so it is taken
    from the previous day's hours, and today's overnight range counts only from its opening time."""
    earlier = _opening_range(previous_hours)
    if isinstance(earlier, tuple) and earlier[1] < earlier[0] and minute < earlier[1]:
        return True
    today = _opening_range(hours)
    if not isinstance(today, tuple):
        return today
    start, end = today
    return start <= minute < end if start < end else minute >= start


def _kenya_now() -> datetime:
    return datetime.now(KENYA_TIME)


def open_now_ids(db: Session) -> list[int]:
    """Facilities whose stored hours for today say they are open now (Kenya time). Facilities without
    readable hours for today are left out rather than guessed, unless they are marked open 24 hours."""
    now = _kenya_now()
    # (today's hours, the previous day's hours): Monday follows Sunday, Saturday follows Friday's weekday hours
    hours_today, hours_before = {
        0: (Facility.weekday_hours, Facility.sunday_hours),
        5: (Facility.saturday_hours, Facility.weekday_hours),
        6: (Facility.sunday_hours, Facility.saturday_hours),
    }.get(now.weekday(), (Facility.weekday_hours, Facility.weekday_hours))
    minute = now.hour * 60 + now.minute
    rows = db.execute(
        select(Facility.id, hours_today.label("today"), hours_before.label("before"), Facility.open_24_hours).where(
            or_(func.trim(hours_today) != "", func.trim(hours_before) != "", Facility.open_24_hours.is_(True))
        )
    ).all()
    open_ids = []
    for facility_id, today, before, always in rows:
        state = open_at(today, minute, before)
        if state or (always and state is None):
            open_ids.append(facility_id)
    return open_ids


def has_published_written_activity():
    """Only visible, written facility activity with the same reply rules as the public page."""
    return (
        select(ExternalPost.id)
        .join(ExternalComment, ExternalComment.post_id == ExternalPost.id)
        .where(
            ExternalPost.facility_id == Facility.id,
            published_external_post(),
            or_(
                ExternalPost.platform == "tiktok",
                and_(ExternalPost.platform == "facebook", ExternalPost.facebook_scope == "facility"),
            ),
            viewable_comment(),
            func.length(func.trim(ExternalComment.text)) > 0,
        )
        .exists()
    )


def build_facility_query(db: Session, filters: dict):
    """Return (select statement, distance expression or None) for the given filters."""
    ratings = rating_subquery()
    query = select(Facility).outerjoin(ratings, ratings.c.facility_id == Facility.id)

    sort = filters.get("sort") or "relevance"
    q = (filters.get("q") or "").strip()
    if q:
        like = f"%{q.lower()}%"
        text_match = or_(
            func.lower(Facility.name).like(like),
            func.lower(Facility.town).like(like),
            func.lower(Facility.area).like(like),
            func.lower(Facility.county).like(like),
            func.lower(Facility.description).like(like),
        )
        service_ids = matching_service_ids(db, q)
        if service_ids:
            offers = select(facility_services.c.facility_id).where(facility_services.c.service_id.in_(service_ids))
            text_match = or_(text_match, Facility.id.in_(offers))
        query = query.where(text_match)

    if filters.get("town"):
        query = query.where(func.lower(Facility.town) == filters["town"].lower())
    if filters.get("county"):
        query = query.where(func.lower(func.trim(Facility.county)).in_(county_filter_labels(filters["county"])))

    types = [t.lower() for t in split_list(filters.get("facility_type"))]
    if types:
        query = query.where(Facility.facility_type.in_(types))
    elif filters.get("exclude_laboratories"):
        query = query.where(Facility.facility_type != "laboratory")

    if filters.get("service"):
        offers = (
            select(facility_services.c.facility_id)
            .join(Service, Service.id == facility_services.c.service_id)
            .where(Service.slug == filters["service"])
        )
        query = query.where(Facility.id.in_(offers))
    if filters.get("insurer"):
        accepts = (
            select(facility_insurers.c.facility_id)
            .join(Insurer, Insurer.id == facility_insurers.c.insurer_id)
            .where(Insurer.slug == filters["insurer"])
        )
        query = query.where(Facility.id.in_(accepts))

    if filters.get("open_weekends"):
        query = query.where(Facility.open_weekends.is_(True))
    if filters.get("open_24_hours"):
        query = query.where(Facility.open_24_hours.is_(True))
    if filters.get("open_now"):
        query = query.where(Facility.id.in_(open_now_ids(db)))
    if filters.get("telehealth"):
        query = query.where(Facility.offers_telehealth.is_(True))
    if filters.get("accepts_requests"):
        query = query.where(Facility.accepts_appointment_requests.is_(True))
    if filters.get("verified_only"):
        query = query.where(Facility.registration_status == "matched")
    if filters.get("hide_demo"):
        query = query.where(Facility.is_demo.is_(False))

    if filters.get("has_patient_reviews"):
        query = query.where(ratings.c.review_count > 0)
    if filters.get("has_public_feedback"):
        query = query.where(has_published_written_activity())

    has_google_rating = filters.get("has_google_rating")
    minimum_google_rating = filters.get("min_google_rating")
    google = None
    if has_google_rating or minimum_google_rating is not None or sort in {"google_rating", "google_count"}:
        google = latest_google_snapshot()
        query = query.outerjoin(google, google.c.facility_id == Facility.id)
        if has_google_rating:
            query = query.where(google.c.rating.is_not(None))
        if minimum_google_rating is not None:
            query = query.where(google.c.rating >= minimum_google_rating)

    distance = None
    lat, lng = filters.get("lat"), filters.get("lng")
    if lat is not None and lng is not None:
        distance = distance_km_expression(lat, lng)
        query = query.where(and_(Facility.latitude.is_not(None), Facility.longitude.is_not(None)))
        if filters.get("radius_km"):
            query = query.where(distance <= filters["radius_km"])

    if sort == "distance" and distance is not None:
        query = query.order_by(distance.asc(), Facility.name)
    elif sort == "rating":
        query = query.order_by(func.coalesce(ratings.c.avg_rating, 0).desc(), func.coalesce(ratings.c.review_count, 0).desc(), Facility.name)
    elif sort == "review_count":
        query = query.order_by(ratings.c.review_count.desc().nulls_last(), Facility.name)
    elif sort == "google_rating":
        query = query.order_by(google.c.rating.desc().nulls_last(), google.c.rating_count.desc().nulls_last(), Facility.name)
    elif sort == "google_count":
        query = query.order_by(google.c.rating_count.desc().nulls_last(), google.c.rating.desc().nulls_last(), Facility.name)
    elif sort == "name":
        query = query.order_by(func.lower(Facility.name))
    elif sort == "name_desc":
        query = query.order_by(func.lower(Facility.name).desc())
    elif sort == "completeness":
        entries = (
            Facility.description, Facility.phone, Facility.website, Facility.address, Facility.weekday_hours,
        )
        completeness = sum(case((func.trim(entry) != "", 1), else_=0) for entry in entries)
        query = query.order_by(completeness.desc(), Facility.is_demo.asc(), Facility.name)
    else:
        # Retain the default ranking for links and existing discovery consumers.
        query = query.order_by(
            Facility.is_demo.asc(), (Facility.registration_status == "matched").desc(), (Facility.phone != "").desc(), Facility.name,
        )

    query = query.order_by(Facility.id)
    query = query.options(selectinload(Facility.services), selectinload(Facility.insurers))
    return query, distance


def ratings_for(db: Session, facility_ids: list[int]) -> dict[int, tuple[float, int]]:
    if not facility_ids:
        return {}
    rows = db.execute(
        select(Review.facility_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.status == "published", Review.facility_id.in_(facility_ids))
        .group_by(Review.facility_id)
    ).all()
    return {fid: (round(float(avg), 1), count) for fid, avg, count in rows}


def google_ratings_for(db: Session, facility_ids: list[int]) -> dict[int, dict]:
    if not facility_ids:
        return {}
    profiles = db.scalars(
        select(FacilityExternalProfile)
        .where(FacilityExternalProfile.facility_id.in_(facility_ids), FacilityExternalProfile.platform == "google",
               FacilityExternalProfile.rating.between(1, 5))
        .order_by(FacilityExternalProfile.fetched_at.desc().nulls_last(), FacilityExternalProfile.id.desc())
    )
    results = {}
    for profile in profiles:
        link = "https://www.google.com/maps/search/?" + urlencode(
            {"api": 1, "query": "Google Maps", "query_place_id": profile.external_id}
        )
        results.setdefault(profile.facility_id, {
            "rating": profile.rating,
            "rating_count": profile.rating_count,
            "url": link,
            "fetched_at": profile.fetched_at.isoformat() if profile.fetched_at else None,
            "attribution": "Rating from Google Maps users. Not a ReproCare rating.",
        })
    return results


def facility_summary(f: Facility, rating: tuple[float, int] | None = None, distance_km: float | None = None) -> dict:
    """Compact shape used by result cards and map markers."""
    return {
        "id": f.id,
        "slug": f.slug,
        "name": f.name,
        "facility_type": f.facility_type,
        "type_label": FACILITY_TYPE_LABELS.get(f.facility_type, f.facility_type),
        "description": f.description,
        "area": f.area,
        "town": f.town,
        "county": f.county,
        "latitude": f.latitude,
        "longitude": f.longitude,
        "phone": f.phone,
        "email": f.email,
        "website": f.website,
        "weekday_hours": f.weekday_hours,
        "open_weekends": f.open_weekends,
        "open_24_hours": f.open_24_hours,
        "offers_telehealth": f.offers_telehealth,
        "accepts_appointment_requests": f.accepts_appointment_requests,
        "registration_status": f.registration_status,
        "services": [{"slug": s.slug, "name": s.name} for s in f.services],
        "insurers": [{"slug": i.slug, "name": i.name} for i in f.insurers],
        "rating": {"average": rating[0], "count": rating[1]} if rating else {"average": None, "count": 0},
        "distance_km": round(distance_km, 1) if distance_km is not None else None,
        "image_key": f.image_key,
        "is_demo": f.is_demo,
    }


def facility_detail(f: Facility, rating: tuple[float, int] | None) -> dict:
    data = facility_summary(f, rating)
    data.update(
        {
            "address": f.address,
            "email": f.email,
            "website": f.website,
            "saturday_hours": f.saturday_hours,
            "sunday_hours": f.sunday_hours,
            "languages": split_list(f.languages),
            "payment_methods": split_list(f.payment_methods),
            "accessibility": split_list(f.accessibility),
            "registration": {
                "status": f.registration_status,
                "body": f.registration_body,
                "code": f.registration_code,
                "checked_on": f.registration_checked_on.isoformat() if f.registration_checked_on else None,
            },
            "lab_tests": [
                {
                    "id": t.id,
                    "name": t.name,
                    "sample_type": t.sample_type,
                    "turnaround": t.turnaround,
                    "price_note": t.price_note,
                    "home_collection": t.home_collection,
                }
                for t in f.lab_tests
            ],
            "source": {
                "code": f.source.code,
                "name": f.source.name,
                "attribution": f.source.attribution,
                "external_id": f.external_id,
            }
            if f.source
            else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
    )
    return data
