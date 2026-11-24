"""Health library articles (public reading, administrator writing) and the Contact Us form."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Article, ContactMessage, Service, User
from app.schemas.contact import ContactCreate
from app.schemas.content import ArticleCreate, ArticleUpdate
from app.services import rate_limit
from app.services.auth_service import get_optional_user, require_role
from app.services.common import make_reference, split_list
from app.services.import_service import slugify

router = APIRouter(tags=["Health library and contact"])
admin_only = require_role("admin")


def article_to_dict(a: Article, full: bool = False) -> dict:
    data = {
        "slug": a.slug,
        "title": a.title,
        "category": a.category,
        "summary": a.summary,
        "read_minutes": a.read_minutes,
        "related_services": split_list(a.related_services),
        "review_status": a.review_status,
        "updated_on": a.updated_on.isoformat() if a.updated_on else None,
    }
    if full:
        data.update({"sections": a.sections, "questions_to_ask": a.questions_to_ask, "references": a.references})
    return data


@router.get("/articles")
def list_articles(q: str | None = Query(None, max_length=100), category: str | None = None, db: Session = Depends(get_db)):
    query = select(Article).where(Article.is_published.is_(True))
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(func.lower(Article.title).like(like), func.lower(Article.summary).like(like), func.lower(Article.category).like(like)))
    if category:
        query = query.where(Article.category == category)
    return [article_to_dict(a) for a in db.scalars(query.order_by(Article.category, Article.title))]


@router.get("/articles/{slug}")
def get_article(slug: str, db: Session = Depends(get_db)):
    # An unpublished article answers exactly like a missing one, so drafts cannot be discovered by slug.
    article = db.scalar(select(Article).where(Article.slug == slug, Article.is_published.is_(True)))
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that article.")
    return article_to_dict(article, full=True)


# --- Administrators: write health library articles ------------------------------------------------


def _related_services(db: Session, slugs: list[str]) -> str:
    """Validated, de-duplicated service slugs, stored comma-separated as the seed data is."""
    wanted = list(dict.fromkeys(s.strip() for s in slugs if s.strip()))
    known = set(db.scalars(select(Service.slug).where(Service.slug.in_(wanted)))) if wanted else set()
    unknown = [s for s in wanted if s not in known]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown related services: {', '.join(unknown)}.")
    return ",".join(wanted)


def _admin_article(db: Session, slug: str) -> Article:
    article = db.scalar(select(Article).where(Article.slug == slug))
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that article.")
    return article


def admin_article_to_dict(a: Article, full: bool = False) -> dict:
    """The public shape plus `is_published`; only administrators see it."""
    return {**article_to_dict(a, full=full), "is_published": a.is_published}


@router.get("/admin/articles")
def admin_articles(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [admin_article_to_dict(a) for a in db.scalars(select(Article).order_by(Article.category, Article.title))]


@router.get("/admin/articles/{slug}")
def admin_article(slug: str, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return admin_article_to_dict(_admin_article(db, slug), full=True)


def _set_published(db: Session, slug: str, published: bool) -> dict:
    article = _admin_article(db, slug)
    article.is_published = published  # publishing is not a content edit, so updated_on is left as it is
    db.commit()
    return admin_article_to_dict(article, full=True)


@router.post("/admin/articles/{slug}/publish")
def publish_article(slug: str, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _set_published(db, slug, True)


@router.post("/admin/articles/{slug}/unpublish")
def unpublish_article(slug: str, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Hides the article from the public library. Nothing is deleted; publishing again restores it."""
    return _set_published(db, slug, False)


@router.post("/admin/articles", status_code=status.HTTP_201_CREATED)
def create_article(body: ArticleCreate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    related = _related_services(db, body.related_services)
    base = slugify(body.title) or "article"
    slug, n = base, 2
    while db.scalar(select(Article.id).where(Article.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    # New articles start as drafts; an administrator publishes them when they are ready.
    article = Article(slug=slug, related_services=related, updated_on=date.today(), is_published=False, **body.stored_fields())
    db.add(article)
    try:
        db.commit()
    except IntegrityError:  # another administrator saved the same slug at the same moment
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Another article with this title was saved at the same time. Please try again.") from None
    db.refresh(article)
    return admin_article_to_dict(article, full=True)


@router.patch("/admin/articles/{slug}")
def update_article(slug: str, body: ArticleUpdate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Edit any field except the slug, so existing links keep working. Records the edit date."""
    article = _admin_article(db, slug)
    changes = body.stored_fields(only_set=True)
    if "related_services" in body.model_fields_set:
        changes["related_services"] = _related_services(db, body.related_services)
    for field, value in changes.items():
        setattr(article, field, value)
    if changes:
        article.updated_on = date.today()
    db.commit()
    return admin_article_to_dict(article, full=True)


# --- Contact Us -------------------------------------------------------------------------------------


def _limit_contact(request: Request, email: str) -> None:
    """Every submission counts (as password recovery requests do): 40 per address and 8 per email in 15 minutes."""
    address = request.client.host if request.client else "unknown"
    keys = (f"ip:contact:{address}", f"contact-email:{email}")
    try:
        rate_limit.check(*keys)
    except HTTPException:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "You have sent several messages in a short time. Please wait 15 minutes and try again."
        ) from None
    rate_limit.record_failure(*keys)


@router.post("/contact", status_code=status.HTTP_201_CREATED)
def send_contact_message(body: ContactCreate, request: Request, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    _limit_contact(request, body.email.lower())
    if body.website:  # filled only by bots
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your message could not be sent.")
    message = ContactMessage(
        reference=make_reference("MSG"),
        user_id=user.id if user else None,
        name=body.name.strip(),
        email=body.email.lower(),
        topic=body.topic,
        message=body.message.strip(),
    )
    db.add(message)
    db.commit()
    return {"reference": message.reference, "status": message.status}
