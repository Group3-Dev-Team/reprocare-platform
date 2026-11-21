"""The data-ingestion endpoint used by the independent ReproCare data bot (or an administrator)."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import User
from app.schemas.data_import import ImportRequest
from app.services.auth_service import get_optional_user
from app.services.import_service import import_facilities

router = APIRouter(prefix="/import", tags=["Data import"])


@router.post("/facilities")
def import_facility_records(
    body: ImportRequest,
    x_import_key: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Accepts either a signed-in administrator or the bot's `X-Import-Key` header."""
    key_ok = bool(settings.import_api_key) and x_import_key is not None and hmac.compare_digest(x_import_key, settings.import_api_key)
    admin_ok = user is not None and user.role == "admin"
    if not (key_ok or admin_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid import key or an administrator session is required.")
    if body.source.code == "demo":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The 'demo' source is reserved for the development seed.")
    return import_facilities(db, body, submitted_by_user_id=user.id if admin_ok else None)
