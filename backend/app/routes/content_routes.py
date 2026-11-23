"""Health library articles and the Contact Us form."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Article, ContactMessage, User
from app.schemas.contact import ContactCreate
from app.services.auth_service import get_optional_user
from app.services.common import make_reference, split_list

router = APIRouter(tags=["Health library and contact"])


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
    query = select(Article)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(func.lower(Article.title).like(like), func.lower(Article.summary).like(like), func.lower(Article.category).like(like)))
    if category:
        query = query.where(Article.category == category)
    return [article_to_dict(a) for a in db.scalars(query.order_by(Article.category, Article.title))]


@router.get("/articles/{slug}")
def get_article(slug: str, db: Session = Depends(get_db)):
    article = db.scalar(select(Article).where(Article.slug == slug))
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that article.")
    return article_to_dict(article, full=True)


@router.post("/contact", status_code=status.HTTP_201_CREATED)
def send_contact_message(body: ContactCreate, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
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
