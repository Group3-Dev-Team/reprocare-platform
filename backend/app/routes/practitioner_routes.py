"""Specialist and practitioner directory."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import Practitioner
from app.services.common import MAX_PAGE_SIZE, paginate, split_list

router = APIRouter(prefix="/practitioners", tags=["Practitioners"])


def practitioner_to_dict(p: Practitioner) -> dict:
    return {
        "id": p.id,
        "slug": p.slug,
        "full_name": p.full_name,
        "title": p.title,
        "specialty": p.specialty,
        "town": p.town,
        "gender": p.gender,
        "languages": split_list(p.languages),
        "offers_telehealth": p.offers_telehealth,
        "bio": p.bio,
        "fee_note": p.fee_note,
        "facility": {"slug": p.facility.slug, "name": p.facility.name, "accepts_appointment_requests": p.facility.accepts_appointment_requests}
        if p.facility
        else None,
        "registration": {
            "status": p.registration_status,
            "body": p.registration_body,
            "code": p.registration_code,
            "checked_on": p.registration_checked_on.isoformat() if p.registration_checked_on else None,
        },
        "is_demo": p.is_demo,
    }


@router.get("")
def search_practitioners(
    q: str | None = Query(None, max_length=100),
    specialty: str | None = None,
    town: str | None = None,
    gender: str | None = Query(None, pattern="^(female|male)$"),
    telehealth: bool = False,
    verified_only: bool = False,
    sort: str = Query("relevance", pattern="^(relevance|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    query = select(Practitioner)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(Practitioner.full_name).like(like),
                func.lower(Practitioner.title).like(like),
                func.lower(Practitioner.specialty).like(like),
                func.lower(Practitioner.bio).like(like),
                func.lower(Practitioner.town).like(like),
            )
        )
    if specialty:
        query = query.where(Practitioner.specialty == specialty)
    if town:
        query = query.where(func.lower(Practitioner.town) == town.lower())
    if gender:
        query = query.where(Practitioner.gender == gender)
    if telehealth:
        query = query.where(Practitioner.offers_telehealth.is_(True))
    if verified_only:
        query = query.where(Practitioner.registration_status == "matched")
    if sort == "name":
        query = query.order_by(Practitioner.full_name)
    else:
        query = query.order_by((Practitioner.registration_status == "matched").desc(), Practitioner.is_demo.asc(), Practitioner.full_name)
    query = query.options(selectinload(Practitioner.facility))
    return paginate(db, query, page, page_size, practitioner_to_dict)


@router.get("/specialties")
def list_specialties(db: Session = Depends(get_db)):
    rows = db.execute(select(Practitioner.specialty, func.count()).group_by(Practitioner.specialty).order_by(Practitioner.specialty)).all()
    return [{"name": name, "count": count} for name, count in rows]


@router.get("/{slug}")
def get_practitioner(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Practitioner).where(Practitioner.slug == slug).options(selectinload(Practitioner.facility)))
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that practitioner.")
    return practitioner_to_dict(p)
