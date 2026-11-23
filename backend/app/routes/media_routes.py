"""Facility photo upload readiness and signed upload parameters (Cloudinary)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Facility, User
from app.services import media_upload
from app.services.auth_service import require_role

router = APIRouter(prefix="/media", tags=["Media"])


class UploadRequest(BaseModel):
    facility_slug: str | None = Field(default=None, max_length=120)
    content_type: str = Field(max_length=60)
    size: int = Field(ge=1)


@router.get("/capabilities")
def capabilities():
    return {"facility_photo_upload": media_upload.enabled(), "max_bytes": media_upload.MAX_BYTES, "types": sorted(media_upload.ALLOWED_TYPES)}


@router.post("/facility-photo/signature")
def facility_photo_signature(body: UploadRequest, user: User = Depends(require_role("facility_staff", "admin")), db: Session = Depends(get_db)):
    if not media_upload.enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Photo uploads are not configured yet.")
    if user.role == "facility_staff":
        facility = db.get(Facility, user.facility_id) if user.facility_id else None
        if facility is None or (body.facility_slug and body.facility_slug != facility.slug):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can upload photos only for your own facility.")
    else:
        facility = db.scalar(select(Facility).where(Facility.slug == (body.facility_slug or "")))
        if facility is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "We could not find that facility.")
    try:
        return media_upload.upload_parameters(facility.slug, body.content_type, body.size)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
