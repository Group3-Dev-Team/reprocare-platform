"""Facility search, filtering, sorting and the JSON shapes the frontend receives."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Facility, Insurer, Review, Service, facility_insurers, facility_services
from app.services.common import split_list

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


def build_facility_query(db: Session, filters: dict):
    """Return (select statement, distance expression or None) for the given filters."""
    ratings = rating_subquery()
    query = select(Facility).outerjoin(ratings, ratings.c.facility_id == Facility.id)

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
        query = query.where(func.lower(Facility.county) == filters["county"].lower())

    types = split_list(filters.get("facility_type"))
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
    if filters.get("telehealth"):
        query = query.where(Facility.offers_telehealth.is_(True))
    if filters.get("accepts_requests"):
        query = query.where(Facility.accepts_appointment_requests.is_(True))
    if filters.get("verified_only"):
        query = query.where(Facility.registration_status == "matched")
    if filters.get("hide_demo"):
        query = query.where(Facility.is_demo.is_(False))

    distance = None
    lat, lng = filters.get("lat"), filters.get("lng")
    if lat is not None and lng is not None:
        distance = distance_km_expression(lat, lng)
        query = query.where(and_(Facility.latitude.is_not(None), Facility.longitude.is_not(None)))
        if filters.get("radius_km"):
            query = query.where(distance <= filters["radius_km"])

    sort = filters.get("sort") or "relevance"
    if sort == "distance" and distance is not None:
        query = query.order_by(distance.asc(), Facility.name)
    elif sort == "rating":
        query = query.order_by(func.coalesce(ratings.c.avg_rating, 0).desc(), func.coalesce(ratings.c.review_count, 0).desc(), Facility.name)
    elif sort == "name":
        query = query.order_by(Facility.name)
    else:  # relevance: real before demo, registry-checked first, then the most complete listings (with contact details)
        query = query.order_by(
            Facility.is_demo.asc(), (Facility.registration_status == "matched").desc(), (Facility.phone != "").desc(), Facility.name
        )

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
