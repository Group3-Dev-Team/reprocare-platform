"""The facility workspace: a facility's own staff maintain its profile and reply to patient experiences."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import AppointmentRequest, Facility, Review, User
from app.schemas.admin import FacilityProfileUpdate
from app.services.auth_service import require_role
from app.services.facility_service import facility_detail, ratings_for

router = APIRouter(prefix="/facility", tags=["Facility workspace"])


def _own_facility(db: Session, user: User) -> Facility:
    facility = db.scalar(
        select(Facility).where(Facility.id == user.facility_id).options(selectinload(Facility.services), selectinload(Facility.insurers), selectinload(Facility.lab_tests), selectinload(Facility.source))
    )
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Your account is not linked to a facility.")
    return facility


@router.get("/overview")
def facility_overview(user: User = Depends(require_role("facility_staff")), db: Session = Depends(get_db)):
    facility = _own_facility(db, user)
    counts = dict(db.execute(select(AppointmentRequest.status, func.count()).where(AppointmentRequest.facility_id == facility.id).group_by(AppointmentRequest.status)).all())
    upcoming = db.scalar(
        select(func.count()).select_from(AppointmentRequest).where(
            AppointmentRequest.facility_id == facility.id, AppointmentRequest.status == "confirmed", AppointmentRequest.preferred_date >= date.today()
        )
    )
    unanswered = db.scalar(select(func.count()).select_from(Review).where(Review.facility_id == facility.id, Review.status == "published", Review.facility_reply == ""))
    return {
        "facility": facility_detail(facility, ratings_for(db, [facility.id]).get(facility.id)),
        "appointments": {"requested": counts.get("requested", 0), "confirmed": counts.get("confirmed", 0), "declined": counts.get("declined", 0), "cancelled": counts.get("cancelled", 0), "upcoming_confirmed": upcoming},
        "reviews_awaiting_reply": unanswered,
    }


@router.patch("/profile")
def update_facility_profile(body: FacilityProfileUpdate, user: User = Depends(require_role("facility_staff")), db: Session = Depends(get_db)):
    facility = _own_facility(db, user)
    for field, value in body.model_dump().items():
        setattr(facility, field, value.strip() if isinstance(value, str) else value)
    facility.open_weekends = bool(facility.saturday_hours.strip() and facility.saturday_hours.lower() != "closed") or bool(
        facility.sunday_hours.strip() and facility.sunday_hours.lower() != "closed"
    ) or facility.open_24_hours
    db.commit()
    return facility_detail(facility, ratings_for(db, [facility.id]).get(facility.id))
