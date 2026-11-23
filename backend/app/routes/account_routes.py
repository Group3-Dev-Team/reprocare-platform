"""The signed-in patient's saved clinics and notifications."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import Facility, Notification, SavedFacility, User
from app.services.auth_service import get_current_user, require_role
from app.services.facility_service import facility_summary, ratings_for

router = APIRouter(prefix="/me", tags=["My account"])


@router.get("/saved")
def saved_facilities(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    # load the services and insurers in one go so each card doesn't run its own query
    rows = db.scalars(
        select(SavedFacility)
        .where(SavedFacility.user_id == user.id)
        .options(selectinload(SavedFacility.facility).selectinload(Facility.services), selectinload(SavedFacility.facility).selectinload(Facility.insurers))
        .order_by(SavedFacility.created_at.desc())
    ).all()
    ratings = ratings_for(db, [r.facility_id for r in rows])
    return [{**facility_summary(r.facility, ratings.get(r.facility_id)), "saved_at": r.created_at.isoformat()} for r in rows]


def _facility_id(db: Session, slug: str) -> int:
    facility_id = db.scalar(select(Facility.id).where(Facility.slug == slug))
    if facility_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    return facility_id


@router.put("/saved/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def save_facility(slug: str, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    facility_id = _facility_id(db, slug)
    # saving twice does nothing
    if db.get(SavedFacility, (user.id, facility_id)) is None:
        db.add(SavedFacility(user_id=user.id, facility_id=facility_id))
        db.commit()


@router.delete("/saved/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_facility(slug: str, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    row = db.get(SavedFacility, (user.id, _facility_id(db, slug)))
    if row:
        db.delete(row)
        db.commit()


@router.get("/notifications")
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(50))
    items = [
        {"id": n.id, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read, "created_at": n.created_at.isoformat()}
        for n in rows
    ]
    # unread count is for the bell badge
    return {"items": items, "unread": sum(1 for n in items if not n["is_read"])}


@router.post("/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)).values(is_read=True))
    db.commit()