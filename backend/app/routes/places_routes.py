
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
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
    request: Request,
    response: Response,
    q: str = Query(min_length=2, max_length=120, description="e.g. 'maternity hospital in Nakuru'"),
    max_results: int = Query(40, ge=1, le=40),
    page_token: str | None = Query(None, max_length=1000),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        if not places.is_configured():
            raise places.PlacesNotConfigured("Google Places is not configured on this server.")
        # one billed request per 20 results
        places.spend_live_requests(_client_key(request), -(-max_results // places.GOOGLE_PAGE_SIZE))
        found = places.text_search(q, max_results=max_results, page_token=page_token)
        listed = _listed_slugs(db, [p["place_id"] for p in found["results"] if p.get("place_id")])
        for p in found["results"]:
            p["facility_slug"] = listed.get(p.get("place_id"))
        return found
    except places.PlacesBudgetExceeded as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    except places.PlacesNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except places.PlacesError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


def _listed_slugs(db: Session, place_ids: list[str]) -> dict[str, str]:
    """Place IDs already linked to a ReproCare listing (confirmed matches only), so live results are not duplicated."""
    if not place_ids:
        return {}
    rows = db.execute(
        select(FacilityExternalProfile.external_id, Facility.slug)
        .join(Facility, Facility.id == FacilityExternalProfile.facility_id)
        .where(FacilityExternalProfile.platform == "google", FacilityExternalProfile.external_id.in_(place_ids))
    )
    return {place_id: slug for place_id, slug in rows}


def _stored_place_id(db: Session, slug: str) -> str | None:
    return db.scalar(
        select(FacilityExternalProfile.external_id)
        .join(Facility, Facility.id == FacilityExternalProfile.facility_id)
        .where(Facility.slug == slug, FacilityExternalProfile.platform == "google")
        .order_by(FacilityExternalProfile.fetched_at.desc().nulls_last(), FacilityExternalProfile.id.desc())
        .limit(1)
    )


def _live(call):
    try:
        if not places.is_configured():
            raise places.PlacesNotConfigured("Google Places is not configured on this server.")
        return call()
    except places.PlacesBudgetExceeded as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except places.PlacesNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except places.PlacesError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


def _photo(place_id: str | None, max_width: int):
    if not place_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This facility does not have a linked Google place.")

    def fetch():
        places.spend_photo_request()
        found = places.place_photo(place_id, max_width=max_width)
        if not found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Google has no photo for this place.")
        return found
    return _live(fetch)


PlaceId = Path(pattern=places.PLACE_ID_PATTERN)


# Cards ask for a summary when they scroll into view, so a visitor gets a larger allowance for these than for searches.
SUMMARIES_PER_CLIENT = 40


@router.get("/facilities/{slug}/summary")
def facility_google_summary(slug: str, request: Request, response: Response, max_width: int = Query(480, ge=120, le=1200),
                            db: Session = Depends(get_db)):
    """Live Google rating (and photo, within the photo cap) for a facility's linked place."""
    response.headers["Cache-Control"] = "no-store"
    place_id = _stored_place_id(db, slug)
    if not place_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This facility does not have a linked Google place.")

    def fetch():
        places.spend_live_requests(_client_key(request), bucket="summary", per_client=SUMMARIES_PER_CLIENT)
        try:
            places.spend_photo_request()
            with_photo = True
        except places.PlacesBudgetExceeded:
            with_photo = False
        return places.place_summary(place_id, with_photo, max_width=max_width)
    return _live(fetch)


@router.get("/facilities/{slug}/photo")
def facility_google_photo(slug: str, response: Response, max_width: int = Query(480, ge=120, le=1200), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return _photo(_stored_place_id(db, slug), max_width)


@router.get("/place/{place_id}")
def live_place(request: Request, response: Response, place_id: str = PlaceId, db: Session = Depends(get_db)):
    """A live Google listing that is not stored by ReproCare. A place already linked to a listing points to it."""
    response.headers["Cache-Control"] = "no-store"
    listed = _listed_slugs(db, [place_id]).get(place_id)
    if listed:
        return {"place_id": place_id, "facility_slug": listed}

    def fetch():
        places.spend_live_requests(_client_key(request))
        return {**places.place_details(place_id), "facility_slug": None}
    return _live(fetch)


@router.get("/place/{place_id}/reviews")
def live_place_reviews(request: Request, response: Response, place_id: str = PlaceId):
    response.headers["Cache-Control"] = "no-store"

    def fetch():
        places.spend_live_requests(_client_key(request))
        return places.written_reviews(place_id)
    return _live(fetch)


@router.get("/place/{place_id}/photo")
def live_place_photo(response: Response, place_id: str = PlaceId, max_width: int = Query(480, ge=120, le=1200)):
    response.headers["Cache-Control"] = "no-store"
    return _photo(place_id, max_width)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/facilities/{slug}/reviews")
def facility_google_reviews(slug: str, request: Request, response: Response, db: Session = Depends(get_db)):
    """Live, attributed Google reviews for a facility's stored Place ID. Nothing is cached or stored."""
    response.headers["Cache-Control"] = "no-store"
    place_id = db.scalar(
        select(FacilityExternalProfile.external_id)
        .join(Facility, Facility.id == FacilityExternalProfile.facility_id)
        .where(Facility.slug == slug, FacilityExternalProfile.platform == "google")
        .order_by(FacilityExternalProfile.fetched_at.desc().nulls_last(), FacilityExternalProfile.id.desc())
        .limit(1)
    )
    if not place_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This facility does not have a linked Google place.")
    try:
        if not places.is_configured():
            raise places.PlacesNotConfigured("Google Places is not configured on this server.")
        places.spend_live_requests(_client_key(request))
        return places.written_reviews(place_id)
    except places.PlacesBudgetExceeded as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except places.PlacesNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except places.PlacesError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
