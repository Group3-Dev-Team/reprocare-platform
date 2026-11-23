"""Appointment requests: patients create and cancel them; the facility's staff confirm or decline them.

A request is never shown as a confirmed appointment until the facility confirms it.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import AppointmentRequest, Facility, Practitioner, Service, User
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule, AppointmentResponse
from app.services.auth_service import require_role
from app.services.common import make_reference, notify, paginate

router = APIRouter(tags=["Appointments"])

LOAD = (
    selectinload(AppointmentRequest.facility),
    selectinload(AppointmentRequest.service),
    selectinload(AppointmentRequest.practitioner),
    selectinload(AppointmentRequest.user),
)


def _resolve_service(db: Session, facility: Facility, slug: str | None) -> Service | None:
    """A named service must exist. When the facility has recorded services, it must be one of them;
    when none are recorded yet, the patient may still say which catalogue service the visit is for."""
    if not slug:
        return None
    service = db.scalar(select(Service).where(Service.slug == slug))
    if service is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "We could not find that service. Choose another or leave it blank.")
    if facility.services and service not in facility.services:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{facility.name} does not list {service.name}. Choose a listed service or leave it blank.")
    return service


def _resolve_practitioner(db: Session, facility: Facility, slug: str | None) -> Practitioner | None:
    if not slug:
        return None
    practitioner = db.scalar(select(Practitioner).where(Practitioner.slug == slug))
    if practitioner is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "We could not find that practitioner. Choose another or leave it blank.")
    if practitioner.facility_id != facility.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{practitioner.full_name} is not listed at {facility.name}.")
    return practitioner


def _pending_duplicate(db: Session, user_id: int, facility_id: int, preferred_date, exclude_id: int | None = None):
    query = select(AppointmentRequest).where(
        AppointmentRequest.user_id == user_id,
        AppointmentRequest.facility_id == facility_id,
        AppointmentRequest.preferred_date == preferred_date,
        AppointmentRequest.status == "requested",
    )
    if exclude_id is not None:
        query = query.where(AppointmentRequest.id != exclude_id)
    return db.scalar(query)


def _transition(db: Session, appointment: AppointmentRequest, allowed: tuple[str, ...], **values) -> None:
    """Change status only if it is still one of ``allowed``. A competing action that already moved the
    request (for example a patient cancelling while staff confirm) makes this one fail with 409."""
    result = db.execute(
        update(AppointmentRequest)
        .where(AppointmentRequest.id == appointment.id, AppointmentRequest.status.in_(allowed))
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        current = db.scalar(select(AppointmentRequest.status).where(AppointmentRequest.id == appointment.id))
        raise HTTPException(status.HTTP_409_CONFLICT, f"This request was just updated and is now {current}. Refresh to see the latest status.")
    db.flush()
    db.refresh(appointment)


def _duplicate_conflict(existing: AppointmentRequest | None) -> HTTPException:
    detail = "You already have a pending request with this facility for that date."
    if existing is not None:
        detail = f"You already have a pending request ({existing.reference}) with this facility for that date."
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def appointment_to_dict(a: AppointmentRequest, for_facility: bool = False) -> dict:
    data = {
        "reference": a.reference,
        "status": a.status,
        "facility": {"slug": a.facility.slug, "name": a.facility.name, "town": a.facility.town, "phone": a.facility.phone},
        "service": {"slug": a.service.slug, "name": a.service.name} if a.service else None,
        "practitioner": {"slug": a.practitioner.slug, "full_name": a.practitioner.full_name} if a.practitioner else None,
        "preferred_date": a.preferred_date.isoformat(),
        "preferred_time": a.preferred_time,
        "contact_phone": a.contact_phone,
        "notes": a.notes,
        "facility_note": a.facility_note,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    if for_facility:
        data["patient"] = {"full_name": a.user.full_name, "email": a.user.email}
    return data


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
def request_appointment(body: AppointmentCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    facility = db.scalar(select(Facility).where(Facility.slug == body.facility_slug))
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    if not facility.accepts_appointment_requests:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This facility does not take requests through ReproCare. Please contact it directly.")
    service = _resolve_service(db, facility, body.service_slug)
    practitioner = _resolve_practitioner(db, facility, body.practitioner_slug)
    duplicate = _pending_duplicate(db, user.id, facility.id, body.preferred_date)
    if duplicate:
        raise _duplicate_conflict(duplicate)

    appointment = AppointmentRequest(
        reference=make_reference("APT"),
        user_id=user.id,
        facility_id=facility.id,
        service_id=service.id if service else None,
        practitioner_id=practitioner.id if practitioner else None,
        preferred_date=body.preferred_date,
        preferred_time=body.preferred_time,
        contact_phone=body.contact_phone.strip(),
        notes=body.notes.strip(),
    )
    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:  # a simultaneous identical request won the unique index
        db.rollback()
        raise _duplicate_conflict(_pending_duplicate(db, user.id, facility.id, body.preferred_date)) from None
    for staff in db.scalars(select(User).where(User.facility_id == facility.id, User.is_active.is_(True))):
        notify(db, staff.id, "New appointment request", f"{appointment.reference} for {body.preferred_date:%d %b %Y}.", "/dashboard/facility/appointments")
    notify(db, user.id, "Request sent", f"{facility.name} has received request {appointment.reference}. It is not confirmed yet.", "/dashboard/appointments")
    db.commit()
    appointment = db.scalar(select(AppointmentRequest).where(AppointmentRequest.id == appointment.id).options(*LOAD))
    return appointment_to_dict(appointment)


@router.get("/me/appointments")
def my_appointments(
    status_filter: str | None = Query(None, alias="status", pattern="^(requested|confirmed|declined|cancelled)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=40),
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    query = select(AppointmentRequest).where(AppointmentRequest.user_id == user.id)
    if status_filter:
        query = query.where(AppointmentRequest.status == status_filter)
    query = query.options(*LOAD).order_by(AppointmentRequest.created_at.desc(), AppointmentRequest.id.desc())
    return paginate(db, query, page, page_size, appointment_to_dict)


@router.post("/me/appointments/{reference}/cancel")
def cancel_appointment(reference: str, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    # Filtering by user_id means another patient's reference returns 404, never someone else's record.
    appointment = db.scalar(
        select(AppointmentRequest).where(AppointmentRequest.reference == reference, AppointmentRequest.user_id == user.id).options(*LOAD)
    )
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that request.")
    if appointment.status not in ("requested", "confirmed"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A {appointment.status} request cannot be cancelled.")
    _transition(db, appointment, ("requested", "confirmed"), status="cancelled")
    for staff in db.scalars(select(User).where(User.facility_id == appointment.facility_id, User.is_active.is_(True))):
        notify(db, staff.id, "Request cancelled by patient", appointment.reference, "/dashboard/facility/appointments")
    db.commit()
    return appointment_to_dict(appointment)


@router.post("/me/appointments/{reference}/reschedule")
def reschedule_appointment(
    reference: str, body: AppointmentReschedule, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)
):
    """Propose a different date or time period. The request returns to 'requested' until the facility responds."""
    appointment = db.scalar(
        select(AppointmentRequest).where(AppointmentRequest.reference == reference, AppointmentRequest.user_id == user.id).options(*LOAD)
    )
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that request.")
    if appointment.status not in ("requested", "confirmed"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A {appointment.status} request cannot be changed. Send a new request instead.")
    if not appointment.facility.accepts_appointment_requests:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This facility no longer takes requests through ReproCare. Please contact it directly.")
    if appointment.preferred_date == body.preferred_date and appointment.preferred_time == body.preferred_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a different date or time of day.")
    duplicate = _pending_duplicate(db, user.id, appointment.facility_id, body.preferred_date, exclude_id=appointment.id)
    if duplicate:
        raise _duplicate_conflict(duplicate)
    note = body.notes.strip()
    try:
        _transition(
            db,
            appointment,
            ("requested", "confirmed"),
            status="requested",
            preferred_date=body.preferred_date,
            preferred_time=body.preferred_time,
            facility_note="",
            **({"notes": note} if note else {}),
        )
    except IntegrityError:
        db.rollback()
        raise _duplicate_conflict(_pending_duplicate(db, user.id, appointment.facility_id, body.preferred_date, appointment.id)) from None
    for staff in db.scalars(select(User).where(User.facility_id == appointment.facility_id, User.is_active.is_(True))):
        notify(
            db,
            staff.id,
            "Patient asked to change a request",
            f"{appointment.reference} now prefers {body.preferred_date:%d %b %Y} ({body.preferred_time}).",
            "/dashboard/facility/appointments",
        )
    notify(db, user.id, "Change requested", f"{appointment.facility.name} will confirm the new date for {appointment.reference}.", "/dashboard/appointments")
    db.commit()
    return appointment_to_dict(appointment)


@router.get("/facility/appointments")
def facility_appointments(
    status_filter: str | None = Query(None, alias="status", pattern="^(requested|confirmed|declined|cancelled)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=40),
    user: User = Depends(require_role("facility_staff")),
    db: Session = Depends(get_db),
):
    query = select(AppointmentRequest).where(AppointmentRequest.facility_id == user.facility_id)
    if status_filter:
        query = query.where(AppointmentRequest.status == status_filter)
    query = query.options(*LOAD).order_by(AppointmentRequest.preferred_date, AppointmentRequest.id)
    return paginate(db, query, page, page_size, lambda a: appointment_to_dict(a, for_facility=True))


@router.patch("/facility/appointments/{reference}")
def respond_to_appointment(
    reference: str, body: AppointmentResponse, user: User = Depends(require_role("facility_staff")), db: Session = Depends(get_db)
):
    appointment = db.scalar(
        select(AppointmentRequest)
        .where(AppointmentRequest.reference == reference, AppointmentRequest.facility_id == user.facility_id)
        .options(*LOAD)
    )
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that request for your facility.")
    if appointment.status != "requested":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This request is already {appointment.status}.")
    _transition(db, appointment, ("requested",), status=body.status, facility_note=body.facility_note.strip())
    word = "confirmed" if body.status == "confirmed" else "declined"
    notify(
        db,
        appointment.user_id,
        f"{appointment.facility.name} {word} your request",
        appointment.facility_note or f"Request {appointment.reference} was {word}.",
        "/dashboard/appointments",
    )
    db.commit()
    return appointment_to_dict(appointment, for_facility=True)
