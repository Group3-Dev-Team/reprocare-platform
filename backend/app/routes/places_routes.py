
from fastapi import APIRouter, HTTPException, Query, status

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
