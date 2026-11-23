"""Create or update ReproCare facilities from Google Places results — without duplicates.

A facility is matched by Google place id (its Google profile, or facilities.external_id as the legacy importer stored it),
never by name. Existing values are only filled in when empty, so details a facility's staff edited are kept.
"""

import re

import bot_config  # noqa: F401  (adds backend/ to sys.path)
from sqlalchemy import or_, select

from app.models import DataSource, Facility, FacilityExternalProfile
from app.services.external_feedback_service import upsert_profile
from google_places import facility_type, opening_hours, photo_refs, town_and_county


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:110] or "facility"


def _unique_slug(db, base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(Facility.id).where(Facility.slug == slug)):
        slug = f"{base[:105]}-{n}"
        n += 1
    return slug


def find_by_place_id(db, place_id: str) -> Facility | None:
    return db.scalar(
        select(Facility)
        .outerjoin(FacilityExternalProfile, (FacilityExternalProfile.facility_id == Facility.id) & (FacilityExternalProfile.platform == "google"))
        .where(or_(FacilityExternalProfile.external_id == place_id, Facility.external_id == place_id))
        .limit(1)
    )


def google_source(db) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.code == "google_places"))
    if source is None:
        source = DataSource(code="google_places", name="Google Places", description="Facility listings discovered with Google Places API (New).", attribution="Listing details from Google Maps")
        db.add(source)
        db.flush()
    return source


def upsert_from_place(db, place: dict, default_town: str = "") -> tuple[Facility | None, str]:
    """Returns (facility, 'created' | 'updated' | 'skipped:<reason>')."""
    place_id = place.get("id")
    name = ((place.get("displayName") or {}).get("text") or "").strip()
    if not place_id or not name:
        return None, "skipped:missing id or name"
    if place.get("businessStatus") == "CLOSED_PERMANENTLY":
        return None, "skipped:permanently closed"

    facility = find_by_place_id(db, place_id)
    town, county = town_and_county(place)
    town, county = town or default_town, county or default_town
    location = place.get("location") or {}
    values = {
        "address": (place.get("formattedAddress") or "")[:255],
        "town": town[:80],
        "county": county[:80],
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "phone": (place.get("nationalPhoneNumber") or "")[:40],
        "website": (place.get("websiteUri") or "")[:255],
        **opening_hours(place),
    }

    if facility is None:
        kind = facility_type(place)
        if kind is None:
            return None, "skipped:not a recognised health facility type"
        if not town:
            return None, "skipped:no town in Google address"
        facility = Facility(
            slug=_unique_slug(db, slugify(name)),
            name=name[:160],
            facility_type=kind,
            description="",
            registration_status="not_checked",
            is_demo=False,
            source_id=google_source(db).id,
            external_id=place_id,
            **values,
        )
        db.add(facility)
        db.flush()
        outcome = "created"
    else:
        for key, value in values.items():
            current = getattr(facility, key)
            if value not in (None, "") and current in (None, "", False):
                setattr(facility, key, value)
        outcome = "updated"

    upsert_profile(
        db,
        facility,
        "google",
        place_id,
        url=place.get("googleMapsUri") or "",
        display_name=name,
        match_method="google_place_id",
        rating=place.get("rating"),
        rating_count=place.get("userRatingCount"),
        photos=photo_refs(place) or None,
        details={"types": place.get("types") or [], "business_status": place.get("businessStatus")},
    )
    return facility, outcome
