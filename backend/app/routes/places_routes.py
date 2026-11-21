"""Live Google Places search (optional; needs GOOGLE_PLACES_API_KEY on the server)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Facility, FacilityExternalProfile

from app.services import google_places_service as places

router = APIRouter(prefix="/places", tags=["Google Places"])


@router.get("/status")
def places_status():
    return {"configured": places.is_configured()}


@router.get("/search")
def search_places(
    q: str = Query(min_length=2, max_length=120, description="e.g. 'maternity hospital in Nakuru'"),
    max_results: int = Query(40, ge=1, le=40),
    page_token: str | None = Query(None, max_length=1000),
):
    try:
        return places.text_search(q, max_results=max_results, page_token=page_token)
    except places.PlacesNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except places.PlacesError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@router.get("/facilities/{slug}/reviews")
def facility_google_reviews(slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    place_id = db.scalar(
        select(FacilityExternalProfile.external_id)
        .join(Facility, Facility.id == FacilityExternalProfile.facility_id)
        .where(Facility.slug == slug, FacilityExternalProfile.platform == "google")
        .order_by(FacilityExternalProfile.fetched_at.desc().nulls_last(), FacilityExternalProfile.id.desc())
        .limit(1)
    )
    if not place_id:
        raise HTTPException(404, "This facility does not have a linked Google place.")
    try:
        return places.written_reviews(place_id)
    except places.PlacesNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except places.PlacesError as exc:
        raise HTTPException(502, str(exc)) from exc
