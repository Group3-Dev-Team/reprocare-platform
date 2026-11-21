"""ReproCare patient reviews: submission, public listing, the patient's own reviews, facility replies and moderation.

Reviews are first-party and moderated. They are kept separate from public feedback collected from other platforms.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import Facility, Review, Service, User
from app.schemas.review import ReviewCreate, ReviewModeration, ReviewReply
from app.services.auth_service import require_role
from app.services.common import MAX_PAGE_SIZE, notify, paginate

router = APIRouter(tags=["Reviews"])


def _get_facility(db: Session, slug: str) -> Facility:
    facility = db.scalar(select(Facility).where(Facility.slug == slug))
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    return facility


def review_to_dict(r: Review, include_status: bool = False) -> dict:
    data = {
        "id": r.id,
        "facility": {"slug": r.facility.slug, "name": r.facility.name, "town": r.facility.town} if r.facility else None,
        "author_name": r.author_name,
        "rating": r.rating,
        "title": r.title,
        "body": r.body,
        "service": {"slug": r.service.slug, "name": r.service.name} if r.service else None,
        "visit_month": r.visit_month.isoformat() if r.visit_month else None,
        "facility_reply": r.facility_reply,
        "source": "ReproCare",
        "is_demo": r.is_demo,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    if include_status:
        data.update({"status": r.status, "moderation_note": r.moderation_note})
    return data


@router.get("/facilities/{slug}/reviews")
def facility_reviews(slug: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=40), db: Session = Depends(get_db)):
    facility = _get_facility(db, slug)
    query = (
        select(Review)
        .where(Review.facility_id == facility.id, Review.status == "published")
        .options(selectinload(Review.facility), selectinload(Review.service))
        .order_by(Review.created_at.desc(), Review.id.desc())
    )
    result = paginate(db, query, page, page_size, review_to_dict)
    distribution = dict(
        db.execute(
            select(Review.rating, func.count()).where(Review.facility_id == facility.id, Review.status == "published").group_by(Review.rating)
        ).all()
    )
    result["distribution"] = {str(star): distribution.get(star, 0) for star in range(5, 0, -1)}
    return result


@router.post("/facilities/{slug}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(slug: str, body: ReviewCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    facility = _get_facility(db, slug)
    if not body.consent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please confirm that your experience can be published after moderation.")
    if db.scalar(select(Review.id).where(Review.facility_id == facility.id, Review.user_id == user.id, Review.status != "rejected")):
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already shared an experience for this facility.")
    service = db.scalar(select(Service).where(Service.slug == body.service_slug)) if body.service_slug else None
    if body.service_slug and service is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "We could not find that service. Choose another or leave it blank.")
    first_name = user.full_name.split()[0]
    surname_initial = (user.full_name.split()[1][0] + ".") if len(user.full_name.split()) > 1 else ""
    review = Review(
        facility_id=facility.id,
        user_id=user.id,
        service_id=service.id if service else None,
        author_name=f"{first_name} {surname_initial}".strip(),
        rating=body.rating,
        title=body.title.strip(),
        body=body.body.strip(),
        visit_month=body.visit_month,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review_to_dict(review, include_status=True)


@router.get("/reviews")
def list_reviews(
    q: str | None = Query(None, max_length=100),
    service: str | None = None,
    town: str | None = None,
    rating: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    """Published ReproCare patient experiences across all facilities (Patient Experiences page)."""
    query = select(Review).join(Facility, Facility.id == Review.facility_id).where(Review.status == "published")
    if q:
        like = f"%{q.lower()}%"
        query = query.where(func.lower(Review.title).like(like) | func.lower(Review.body).like(like) | func.lower(Facility.name).like(like))
    if service:
        query = query.join(Service, Service.id == Review.service_id).where(Service.slug == service)
    if town:
        query = query.where(func.lower(Facility.town) == town.lower())
    if rating:
        query = query.where(Review.rating == rating)
    query = query.options(selectinload(Review.facility), selectinload(Review.service)).order_by(Review.created_at.desc(), Review.id.desc())
    return paginate(db, query, page, page_size, review_to_dict)


@router.get("/me/reviews")
def my_reviews(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Review).where(Review.user_id == user.id).options(selectinload(Review.facility), selectinload(Review.service)).order_by(Review.created_at.desc())
    )
    return [review_to_dict(r, include_status=True) for r in rows]


@router.get("/facility/reviews")
def own_facility_reviews(user: User = Depends(require_role("facility_staff")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Review).where(Review.facility_id == user.facility_id, Review.status == "published").options(selectinload(Review.facility), selectinload(Review.service)).order_by(Review.created_at.desc())
    )
    return [review_to_dict(r) for r in rows]


@router.put("/facility/reviews/{review_id}/reply")
def reply_to_review(review_id: int, body: ReviewReply, user: User = Depends(require_role("facility_staff")), db: Session = Depends(get_db)):
    review = db.scalar(select(Review).where(Review.id == review_id, Review.facility_id == user.facility_id, Review.status == "published").options(selectinload(Review.facility), selectinload(Review.service)))
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that review for your facility.")
    review.facility_reply = body.reply.strip()
    db.commit()
    return review_to_dict(review)


@router.get("/admin/reviews")
def reviews_for_moderation(
    status_filter: str = Query("pending", alias="status", pattern="^(pending|published|rejected)$"),
    page: int = Query(1, ge=1),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = select(Review).where(Review.status == status_filter).options(selectinload(Review.facility), selectinload(Review.service)).order_by(Review.created_at.desc())
    return paginate(db, query, page, 20, lambda r: review_to_dict(r, include_status=True))


@router.post("/admin/reviews/{review_id}/moderate")
def moderate_review(review_id: int, body: ReviewModeration, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    review = db.scalar(select(Review).where(Review.id == review_id).options(selectinload(Review.facility), selectinload(Review.service)))
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found.")
    review.status = body.decision
    review.moderation_note = body.note.strip()
    if review.user_id:
        word = "is now published" if body.decision == "published" else "was not published"
        notify(db, review.user_id, f"Your review {word}", body.note.strip() or review.title, "/dashboard/reviews")
    db.commit()
    return review_to_dict(review, include_status=True)
