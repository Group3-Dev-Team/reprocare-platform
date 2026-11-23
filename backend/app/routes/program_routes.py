"""Community health programmes: browse, register, cancel; administrators publish and manage them."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import CommunityProgram, ProgramRegistration, Service, User
from app.schemas.program import ProgramCreate, ProgramUpdate, RegistrationCreate
from app.services.auth_service import require_role
from app.services.common import MAX_PAGE_SIZE, make_reference, notify, paginate
from app.services.import_service import slugify

router = APIRouter(tags=["Community programmes"])


def registered_counts(db: Session, program_ids: list[int]) -> dict[int, int]:
    if not program_ids:
        return {}
    rows = db.execute(
        select(ProgramRegistration.program_id, func.count())
        .where(ProgramRegistration.program_id.in_(program_ids), ProgramRegistration.status != "cancelled")
        .group_by(ProgramRegistration.program_id)
    ).all()
    return dict(rows)


def program_to_dict(p: CommunityProgram, registered: int = 0) -> dict:
    return {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "program_type": p.program_type,
        "summary": p.summary,
        "description": p.description,
        "organizer_name": p.organizer_name,
        "service": {"slug": p.service.slug, "name": p.service.name} if p.service else None,
        "host_facility": {"slug": p.host_facility.slug, "name": p.host_facility.name} if p.host_facility else None,
        "venue": p.venue,
        "town": p.town,
        "county": p.county,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "start_date": p.start_date.isoformat(),
        "start_time": p.start_time,
        "end_time": p.end_time,
        "eligibility": p.eligibility,
        "requirements": p.requirements,
        "cost_type": p.cost_type,
        "cost_note": p.cost_note,
        "capacity": p.capacity,
        "registered": registered,
        "spaces_left": max(p.capacity - registered, 0),
        "status": p.status,
        "is_past": p.start_date < date.today(),
        "is_demo": p.is_demo,
    }


LOAD = (selectinload(CommunityProgram.service), selectinload(CommunityProgram.host_facility))


@router.get("/programs")
def list_programs(
    q: str | None = Query(None, max_length=100),
    town: str | None = None,
    program_type: str | None = Query(None, pattern="^(screening|testing|education|outreach)$"),
    cost_type: str | None = Query(None, description="free, subsidised or paid; comma-separated allowed"),
    service: str | None = None,
    include_past: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    query = select(CommunityProgram).where(CommunityProgram.status == "published")
    if not include_past:
        query = query.where(CommunityProgram.start_date >= date.today())
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(func.lower(CommunityProgram.title).like(like), func.lower(CommunityProgram.summary).like(like), func.lower(CommunityProgram.organizer_name).like(like), func.lower(CommunityProgram.town).like(like))
        )
    if town:
        query = query.where(func.lower(CommunityProgram.town) == town.lower())
    if program_type:
        query = query.where(CommunityProgram.program_type == program_type)
    if cost_type:
        query = query.where(CommunityProgram.cost_type.in_([c.strip() for c in cost_type.split(",") if c.strip()]))
    if service:
        query = query.join(Service, Service.id == CommunityProgram.service_id).where(Service.slug == service)
    query = query.options(*LOAD).order_by(CommunityProgram.start_date, CommunityProgram.title)
    result = paginate(db, query, page, page_size, lambda p: p)
    counts = registered_counts(db, [p.id for p in result["items"]])
    result["items"] = [program_to_dict(p, counts.get(p.id, 0)) for p in result["items"]]
    return result


def _get_program(db: Session, slug: str, published_only: bool = True) -> CommunityProgram:
    query = select(CommunityProgram).where(CommunityProgram.slug == slug).options(*LOAD)
    if published_only:
        query = query.where(CommunityProgram.status == "published")
    program = db.scalar(query)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that programme.")
    return program


@router.get("/programs/{slug}")
def get_program(slug: str, db: Session = Depends(get_db)):
    program = _get_program(db, slug)
    return program_to_dict(program, registered_counts(db, [program.id]).get(program.id, 0))


def registration_to_dict(r: ProgramRegistration, include_program: bool = True) -> dict:
    data = {"reference": r.reference, "status": r.status, "full_name": r.full_name, "phone": r.phone, "created_at": r.created_at.isoformat() if r.created_at else None}
    if include_program:
        p = r.program
        data["program"] = {"slug": p.slug, "title": p.title, "venue": p.venue, "town": p.town, "start_date": p.start_date.isoformat(), "start_time": p.start_time, "end_time": p.end_time, "status": p.status, "is_demo": p.is_demo}
    return data


@router.post("/programs/{slug}/registrations", status_code=status.HTTP_201_CREATED)
def register_for_program(slug: str, body: RegistrationCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please agree that the organiser may use your name and phone number for this programme.")
    # Lock the programme row so two people cannot take the last space at the same time.
    program = db.scalar(select(CommunityProgram).where(CommunityProgram.slug == slug, CommunityProgram.status == "published").with_for_update())
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that programme.")
    if program.start_date < date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration has closed for this programme.")
    existing = db.scalar(select(ProgramRegistration).where(ProgramRegistration.program_id == program.id, ProgramRegistration.user_id == user.id))
    if existing and existing.status != "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, f"You are already registered (reference {existing.reference}).")
    if registered_counts(db, [program.id]).get(program.id, 0) >= program.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "This programme is full.")
    if existing:  # re-registering after a cancellation reuses the row (one row per person per programme)
        existing.status, existing.full_name, existing.phone = "registered", body.full_name.strip(), body.phone.strip()
        registration = existing
    else:
        registration = ProgramRegistration(reference=make_reference("REG"), program_id=program.id, user_id=user.id, full_name=body.full_name.strip(), phone=body.phone.strip())
        db.add(registration)
    notify(db, user.id, "Registration confirmed", f"{program.title} on {program.start_date:%d %b %Y}. Reference {registration.reference}.", "/dashboard/registrations")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You are already registered for this programme.")
    db.refresh(registration)
    return registration_to_dict(registration)


@router.get("/me/registrations")
def my_registrations(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ProgramRegistration).where(ProgramRegistration.user_id == user.id).options(selectinload(ProgramRegistration.program)).order_by(ProgramRegistration.created_at.desc())
    )
    return [registration_to_dict(r) for r in rows]


@router.post("/me/registrations/{reference}/cancel")
def cancel_registration(reference: str, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    registration = db.scalar(
        select(ProgramRegistration).where(ProgramRegistration.reference == reference, ProgramRegistration.user_id == user.id).options(selectinload(ProgramRegistration.program))
    )
    if registration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that registration.")
    if registration.status != "registered":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only an active registration can be cancelled.")
    registration.status = "cancelled"
    db.commit()
    return registration_to_dict(registration)


# --- Administrators -------------------------------------------------------------------------------


@router.get("/admin/programs")
def admin_programs(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(CommunityProgram).options(*LOAD).order_by(CommunityProgram.start_date.desc())).all()
    counts = registered_counts(db, [p.id for p in rows])
    return [program_to_dict(p, counts.get(p.id, 0)) for p in rows]


@router.post("/admin/programs", status_code=status.HTTP_201_CREATED)
def create_program(body: ProgramCreate, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    service = db.scalar(select(Service).where(Service.slug == body.service_slug)) if body.service_slug else None
    base = slugify(f"{body.title} {body.town}")
    slug, n = base, 2
    while db.scalar(select(CommunityProgram.id).where(CommunityProgram.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    data = body.model_dump(exclude={"service_slug"})
    program = CommunityProgram(slug=slug, service_id=service.id if service else None, **data)
    db.add(program)
    db.commit()
    return program_to_dict(_get_program(db, slug, published_only=False))


@router.patch("/admin/programs/{slug}")
def update_program(slug: str, body: ProgramUpdate, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    program = _get_program(db, slug, published_only=False)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(program, field, value)
    db.commit()
    return program_to_dict(program, registered_counts(db, [program.id]).get(program.id, 0))


@router.get("/admin/programs/{slug}/registrations")
def program_registrations(slug: str, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    program = _get_program(db, slug, published_only=False)
    rows = db.scalars(select(ProgramRegistration).where(ProgramRegistration.program_id == program.id).order_by(ProgramRegistration.created_at))
    return [registration_to_dict(r, include_program=False) for r in rows]
