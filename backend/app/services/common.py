"""Small helpers shared by several routes: references, pagination, comma-separated lists, notifications."""

import math
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Notification

MAX_PAGE_SIZE = 40  # the interface shows up to 40 results per page


def make_reference(prefix: str) -> str:
    """Human-readable reference such as 'APT-7K3Q9X' (no 0/O/1/I to avoid confusion)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return f"{prefix}-" + "".join(secrets.choice(alphabet) for _ in range(6))


def paginate(db: Session, query, page: int, page_size: int, serialize) -> dict:
    """Run a SELECT with LIMIT/OFFSET and return the standard list envelope used by every list endpoint."""
    page = max(page, 1)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return {
        "items": [serialize(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def split_list(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def join_list(values: list[str] | None) -> str:
    return ", ".join(v.strip() for v in (values or []) if v and v.strip())


def notify(db: Session, user_id: int, title: str, body: str = "", link: str | None = None) -> None:
    """Add an in-app notification. The caller commits."""
    db.add(Notification(user_id=user_id, title=title, body=body, link=link))
