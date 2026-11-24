"""Reference lists used to build search filters, plus homepage figures and a health check."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import CommunityProgram, Facility, Insurer, Practitioner, Review, Service
from app.services.county_service import KENYA_COUNTIES, county_key
from app.services.common import split_list

router = APIRouter(tags=["Reference data"])


@router.get("/health/ready", tags=["Health"])
def health_ready(db: Session = Depends(get_db)):
    """Readiness check: confirms the database answers. /api/health (main.py) is the lightweight liveness check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/services")
def list_services(db: Session = Depends(get_db)):
    rows = db.scalars(select(Service).order_by(Service.name))
    return [{"slug": s.slug, "name": s.name, "short_description": s.short_description, "keywords": split_list(s.keywords)} for s in rows]


@router.get("/insurers")
def list_insurers(db: Session = Depends(get_db)):
    rows = db.scalars(select(Insurer).order_by(Insurer.name))
    return [{"slug": i.slug, "name": i.name, "kind": i.kind, "note": i.note} for i in rows]


@router.get("/towns")
def list_towns(db: Session = Depends(get_db)):
    """Towns that have at least one facility, with a facility count and an approximate centre for the map."""
    rows = db.execute(
        select(Facility.town, Facility.county, func.count(Facility.id), func.avg(Facility.latitude), func.avg(Facility.longitude))
        .group_by(Facility.town, Facility.county)
        .order_by(func.count(Facility.id).desc(), Facility.town)
    ).all()
    return [
        {"town": t, "county": c, "facility_count": n, "latitude": round(lat, 4) if lat else None, "longitude": round(lng, 4) if lng else None}
        for t, c, n, lat, lng in rows
    ]


@router.get("/stats")
def platform_stats(db: Session = Depends(get_db)):
    """Counts shown on the homepage. Demonstration records are counted separately so nothing is overstated."""
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    return {
        "facilities": count(Facility),
        "facilities_demo": count(Facility, Facility.is_demo.is_(True)),
        "registry_matched": count(Facility, Facility.registration_status == "matched"),
        "practitioners": count(Practitioner),
        "laboratories": count(Facility, Facility.facility_type == "laboratory"),
        "upcoming_programs": count(CommunityProgram, CommunityProgram.status == "published", CommunityProgram.start_date >= date.today()),
        "published_reviews": count(Review, Review.status == "published"),
        "towns": db.scalar(select(func.count(func.distinct(Facility.town)))) or 0,
        "services": count(Service),
    }


@router.get("/counties")
def list_counties(db: Session = Depends(get_db)):
    """All Kenyan counties, with actual imported facility counts."""
    rows = db.execute(
        select(Facility.county, func.count(Facility.id))
        .group_by(Facility.county)
    ).all()
    counts = {}
    for name, count in rows:
        key = county_key(name)
        counts[key] = counts.get(key, 0) + count

    return [
        {"county": county, "facility_count": counts.get(county.casefold(), 0)}
        for county in KENYA_COUNTIES
    ]
