"""Platform administration: overview, review moderation, accounts, contact messages and import history."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import AppointmentRequest, CommunityProgram, ContactMessage, Facility, ImportBatch, ProgramRegistration, Review, User


router = APIRouter(prefix="/admin", tags=["Administration"])
admin_only = require_role("admin")


def _count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


@router.get("/overview")
def overview(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return {
        "users": dict(db.execute(select(User.role, func.count()).group_by(User.role)).all()),
        "facilities": _count(db, Facility),
        "facilities_demo": _count(db, Facility, Facility.is_demo.is_(True)),
        "reviews_pending": _count(db, Review, Review.status == "pending"),
        "contact_new": _count(db, ContactMessage, ContactMessage.status == "new"),
        "appointments_open": _count(db, AppointmentRequest, AppointmentRequest.status == "requested"),
        "programs_upcoming": _count(db, CommunityProgram, CommunityProgram.status == "published", CommunityProgram.start_date >= date.today()),
        "registrations_active": _count(db, ProgramRegistration, ProgramRegistration.status == "registered"),
        "import_batches": _count(db, ImportBatch),
    }



@router.get("/users")
def list_users(
    role: str | None = Query(None, pattern="^(patient|facility_staff|admin)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    query = select(User).options(selectinload(User.facility))
    if role:
        query = query.where(User.role == role)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    return paginate(db, query.order_by(User.created_at.desc(), User.id.desc()), page, 20, user_to_dict)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_staff_account(body: StaffAccountCreate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    facility_id = None
    if body.role == "facility_staff":
        facility_id = db.scalar(select(Facility.id).where(Facility.slug == (body.facility_slug or "")))
        if facility_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose the facility this staff account belongs to.")
    account = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role=body.role, facility_id=facility_id)
    db.add(account)
n
    db.refresh(account)
    return user_to_dict(account)


@router.patch("/users/{user_id}")
def set_user_status(user_id: int, body: UserStatusUpdate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    account = db.get(User, user_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if account.id == user.id and not body.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account.")
    account.is_active = body.is_active
    db.commit()
    return user_to_dict(account)


@router.get("/contact-messages")
def contact_messages(
    status_filter: str | None = Query(None, alias="status", pattern="^(new|in_progress|resolved)$"),
    page: int = Query(1, ge=1),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    query = select(ContactMessage)
    if status_filter:
        query = query.where(ContactMessage.status == status_filter)

    def shape(m: ContactMessage) -> dict:
        return {"reference": m.reference, "name": m.name, "email": m.email, "topic": m.topic, "message": m.message, "status": m.status, "created_at": m.created_at.isoformat()}

    return paginate(db, query.order_by(ContactMessage.created_at.desc(), ContactMessage.id.desc()), page, 20, shape)


@router.patch("/contact-messages/{reference}")
def update_contact_message(reference: str, body: ContactStatusUpdate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    message = db.scalar(select(ContactMessage).where(ContactMessage.reference == reference))
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    message.status = body.status
    db.commit()
    return {"reference": message.reference, "status": message.status}


@router.get("/imports")
def import_history(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(ImportBatch).options(selectinload(ImportBatch.source)).order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc()).limit(50))
    return [
        {
            "id": b.id,
            "source": b.source.code,
            "received": b.received_count,
            "created": b.created_count,
            "updated": b.updated_count,
            "failed": b.error_count,
            "errors": b.errors,
            "created_at": b.created_at.isoformat(),
        }
        for b in rows
    ]
