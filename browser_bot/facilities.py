"""Create or update ReproCare facilities from Google Places results — without duplicates.

A facility is matched by Google place id (its Google profile, or facilities.external_id as the legacy importer stored it),
never by name. Existing values are only filled in when empty, so details a facility's staff edited are kept.

A place with no linked facility is NOT created when a facility with the same name already stands within
DUPLICATE_RADIUS_M (for example an OpenStreetMap facility that has no Google place id yet). It is reported for review;
a person links the place id with `reprocare_bot.py link-google` once they have checked it is the same facility.
"""

import math
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


DUPLICATE_RADIUS_M = 300
_NAME_NOISE = {"the", "ltd", "limited"}


def name_key(name: str) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9]+", name.casefold().replace("&", " and "))
    return tuple(w for w in words if w not in _NAME_NOISE)


def _metres(lat1, lng1, lat2, lng2) -> float:
    p = math.pi / 180
    h = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2
    return 12_742_000 * math.asin(math.sqrt(h))


def possible_duplicate(db, name: str, latitude, longitude) -> Facility | None:
    """An existing facility with the same name (ignoring case, punctuation and 'Ltd') within DUPLICATE_RADIUS_M."""
    if latitude is None or longitude is None:
        return None
    key = name_key(name)
    box = 0.01  # about 1.1 km, narrowed by the exact distance below
    nearby = db.scalars(
        select(Facility).where(
            Facility.latitude.between(latitude - box, latitude + box),
            Facility.longitude.between(longitude - box, longitude + box),
        ).order_by(Facility.id)
    )
    for facility in nearby:
        if name_key(facility.name) == key and _metres(latitude, longitude, facility.latitude, facility.longitude) <= DUPLICATE_RADIUS_M:
            return facility
    return None


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
        existing = possible_duplicate(db, name, location.get("latitude"), location.get("longitude"))
        if existing is not None:
            return None, f"skipped:possible duplicate of {existing.slug}"
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
