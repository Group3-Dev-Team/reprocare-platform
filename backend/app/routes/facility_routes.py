"""Public facility discovery: search, filters, pagination, map markers, details and patient experiences."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import Facility, LabTest, Practitioner
from app.services.common import MAX_PAGE_SIZE, paginate
from app.services.facility_service import build_facility_query, facility_detail, facility_summary, google_ratings_for, ratings_for

router = APIRouter(tags=["Facilities"])


def _haversine(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(d))


def facility_filters(
    q: str | None = Query(None, max_length=100, description="Name, town, area or service, e.g. 'antenatal Kisumu'"),
    town: str | None = Query(None, max_length=80),
    county: str | None = Query(None, max_length=80),
    facility_type: str | None = Query(None, description="One or more of hospital, clinic, maternity_home, health_centre, laboratory (comma-separated)"),
    service: str | None = Query(None, description="Service slug, e.g. 'cervical'"),
    insurer: str | None = Query(None, description="Insurer slug, e.g. 'sha'"),
    open_weekends: bool = False,
    open_24_hours: bool = False,
    open_now: bool = Query(False, description="Open at this moment (Kenya time), from the stored opening hours"),
    telehealth: bool = False,
    accepts_requests: bool = False,
    verified_only: bool = False,
    hide_demo: bool = False,
    exclude_laboratories: bool = False,
    has_patient_reviews: bool = False,
    has_public_feedback: bool = False,
    has_google_rating: bool = False,
    min_google_rating: float | None = Query(None, ge=1, le=5),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0, le=1000),
    sort: str = Query("relevance", pattern="^(relevance|name|name_desc|rating|review_count|google_rating|google_count|completeness|distance)$"),
) -> dict:
    return locals()


@router.get("/facilities")
def search_facilities(
    filters: dict = Depends(facility_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    query, _ = build_facility_query(db, filters)
    result = paginate(db, query, page, page_size, lambda f: f)
    ids = [f.id for f in result["items"]]
    ratings = ratings_for(db, ids)
    google = google_ratings_for(db, ids)
    result["items"] = [
        {**facility_summary(f, ratings.get(f.id), _haversine(filters["lat"], filters["lng"], f.latitude, f.longitude)),
         "google_rating": google.get(f.id)}
        for f in result["items"]
    ]
    return result


@router.get("/facilities/markers")
def facility_markers(filters: dict = Depends(facility_filters), db: Session = Depends(get_db)):
    """Every matching facility that has stored coordinates (up to 1,000), in a light shape for the map."""
    query, _ = build_facility_query(db, filters)
    rows = db.scalars(query.where(Facility.latitude.is_not(None), Facility.longitude.is_not(None)).limit(1000)).unique().all()
    return [
        {"slug": f.slug, "name": f.name, "facility_type": f.facility_type, "town": f.town, "latitude": f.latitude, "longitude": f.longitude, "is_demo": f.is_demo}
        for f in rows
    ]


def _get_facility(db: Session, slug: str) -> Facility:
    facility = db.scalar(
        select(Facility)
        .where(Facility.slug == slug)
        .options(selectinload(Facility.services), selectinload(Facility.insurers), selectinload(Facility.lab_tests), selectinload(Facility.source))
    )
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    return facility


@router.get("/facilities/{slug}")
def get_facility(slug: str, db: Session = Depends(get_db)):
    facility = _get_facility(db, slug)
    data = facility_detail(facility, ratings_for(db, [facility.id]).get(facility.id))
    data["practitioners"] = [
        {"slug": p.slug, "full_name": p.full_name, "title": p.title, "specialty": p.specialty, "is_demo": p.is_demo}
        for p in db.scalars(select(Practitioner).where(Practitioner.facility_id == facility.id).order_by(Practitioner.full_name))
    ]
    return data


@router.get("/lab-tests")
def search_lab_tests(
    q: str | None = Query(None, max_length=100),
    town: str | None = None,
    home_collection: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    query = select(LabTest).join(Facility, Facility.id == LabTest.facility_id)
    if q:
        query = query.where(func.lower(LabTest.name).like(f"%{q.lower()}%"))
    if town:
        query = query.where(func.lower(Facility.town) == town.lower())
    if home_collection:
        query = query.where(LabTest.home_collection.is_(True))
    query = query.options(selectinload(LabTest.facility)).order_by(LabTest.name, Facility.name)

    def shape(t: LabTest) -> dict:
        return {
            "id": t.id,
            "name": t.name,
            "sample_type": t.sample_type,
            "turnaround": t.turnaround,
            "price_note": t.price_note,
            "home_collection": t.home_collection,
            "facility": {"slug": t.facility.slug, "name": t.facility.name, "town": t.facility.town, "is_demo": t.facility.is_demo},
        }

    return paginate(db, query, page, page_size, shape)
