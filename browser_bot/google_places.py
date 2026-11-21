"""Google Places API (New): facility discovery (Text Search) and details (Place Details).

Billing: every call is billed by Google according to the fields requested. Text Search with website/phone/
rating fields and Place Details with reviews/photos fall in the higher (Enterprise / Enterprise + Atmosphere)
SKUs. Requests are capped per day (places_cache.DAILY_LIMIT) and details are cached for CACHE_DAYS.

Google content policy: the place id may be stored indefinitely; other content is refreshed by re-running
`reprocare_bot.py google`. Photos are stored as REFERENCES (resource names + author attributions), never
downloaded; reviews are stored with their Google attribution and shown labelled as Google reviews.
"""

import json
import re
import urllib.error
import urllib.request

from bot_config import google_api_key
from places_cache import cached_request

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

SEARCH_FIELDS = ",".join(
    "places." + f
    for f in (
        "id", "displayName", "formattedAddress", "addressComponents", "location", "types",
        "websiteUri", "nationalPhoneNumber", "googleMapsUri", "rating", "userRatingCount", "businessStatus",
    )
) + ",nextPageToken"

DETAIL_FIELDS = ",".join(
    (
        "id", "displayName", "formattedAddress", "addressComponents", "location", "types", "websiteUri",
        "nationalPhoneNumber", "googleMapsUri", "rating", "userRatingCount", "regularOpeningHours",
        "reviews", "photos", "businessStatus",
    )
)


class PlacesUnavailable(RuntimeError):
    pass


def _post(url: str, body: dict, field_mask: str) -> dict:
    key = google_api_key()
    if not key:
        raise PlacesUnavailable("GOOGLE_PLACES_API_KEY is not set in backend/.env")
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": field_mask},
        method="POST",
    )
    return _send(request)


def _get(url: str, field_mask: str) -> dict:
    key = google_api_key()
    if not key:
        raise PlacesUnavailable("GOOGLE_PLACES_API_KEY is not set in backend/.env")
    request = urllib.request.Request(url, headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": field_mask})
    return _send(request)


def _send(request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Google's error body explains quota/billing/field problems; it never contains the key.
        try:
            message = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            message = ""
        raise PlacesUnavailable(f"Google Places HTTP {exc.code}: {message[:300]}") from None
    except urllib.error.URLError as exc:
        raise PlacesUnavailable(f"Could not reach Google Places ({type(exc.reason).__name__})") from None


def text_search(query: str, page_size: int = 20) -> list[dict]:
    """One billed request (cached for the day by query)."""
    body = {"textQuery": query, "pageSize": max(1, min(page_size, 20)), "regionCode": "KE", "languageCode": "en"}
    data = cached_request("search:" + query.casefold(), lambda: _post(TEXT_SEARCH_URL, body, SEARCH_FIELDS))
    return (data or {}).get("places", [])


def place_details(place_id: str, refresh: bool = False) -> dict | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,255}", place_id or ""):
        raise PlacesUnavailable("Invalid place id")
    return cached_request("details:" + place_id, lambda: _get(DETAILS_URL.format(place_id=place_id), DETAIL_FIELDS), refresh=refresh)


# --------------------------------------------------------------------------- shaping

FACILITY_KEYWORDS = (
    ("maternity_home", ("maternity", "nursing home")),
    ("laboratory", ("laborator", "diagnostic", "pathology", "lab ")),
    ("hospital", ("hospital",)),
    ("health_centre", ("health centre", "health center", "dispensary")),
    ("clinic", ("clinic", "medical centre", "medical center", "fertility", "women's health")),
)


def facility_type(place: dict) -> str | None:
    """Same idea as the legacy scripts' expand_facilities.facility_type, extended to laboratories."""
    name = (place.get("displayName") or {}).get("text", "").casefold() + " "
    types = set(place.get("types") or [])
    if "maternity" in name and "hospital" not in name:
        return "maternity_home"
    for kind, words in FACILITY_KEYWORDS:
        if any(w in name for w in words):
            return kind
    if "hospital" in types:
        return "hospital"
    if types & {"medical_lab"}:
        return "laboratory"
    if types & {"medical_clinic", "doctor", "health"}:
        return "clinic"
    return None


def _component(place: dict, kind: str) -> str:
    for comp in place.get("addressComponents") or []:
        if kind in (comp.get("types") or []):
            return comp.get("longText") or comp.get("shortText") or ""
    return ""


def town_and_county(place: dict) -> tuple[str, str]:
    county = re.sub(r"\s+County$", "", _component(place, "administrative_area_level_1")).strip()
    town = _component(place, "locality") or _component(place, "postal_town") or _component(place, "administrative_area_level_2")
    town = re.sub(r"\s+County$", "", town).strip()
    return town or county, county or town


def opening_hours(place: dict) -> dict:
    """Map regularOpeningHours.weekdayDescriptions ('Monday: 8:00 AM – 5:00 PM') onto ReproCare's fields."""
    lines = (place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
    days = {}
    for line in lines:
        day, _, hours = line.partition(":")
        days[day.strip().casefold()] = hours.strip()
    if not days:
        return {}
    weekday = days.get("monday") or days.get("tuesday") or ""
    always = days and all(v.casefold().startswith("open 24 hours") for v in days.values())
    sat, sun = days.get("saturday", ""), days.get("sunday", "")
    return {
        "weekday_hours": weekday[:60],
        "saturday_hours": sat[:60],
        "sunday_hours": sun[:60],
        "open_24_hours": bool(always),
        "open_weekends": any(v and v.casefold() != "closed" for v in (sat, sun)),
    }


def photo_refs(place: dict) -> list[dict]:
    return [
        {
            "name": p.get("name"),
            "width": p.get("widthPx"),
            "height": p.get("heightPx"),
            "attributions": [a.get("displayName") for a in (p.get("authorAttributions") or []) if a.get("displayName")],
        }
        for p in (place.get("photos") or [])[:10]
        if p.get("name")
    ]


def reviews_batch(place: dict, facility_slug: str) -> dict | None:
    """Google reviews returned by Place Details (at most 5, chosen by Google) as one import batch."""
    place_id = place.get("id")
    url = place.get("googleMapsUri") or f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    comments = []
    for review in place.get("reviews") or []:
        text = ((review.get("originalText") or review.get("text") or {}).get("text") or "").strip()
        rating = review.get("rating")
        comments.append(
            {
                "external_id": review.get("name") or f"{place_id}:{review.get('publishTime')}",
                "author_name": (review.get("authorAttribution") or {}).get("displayName", ""),
                "text": text,
                "published_at": review.get("publishTime"),
                "source_rating": int(rating) if isinstance(rating, (int, float)) and 1 <= rating <= 5 else None,
            }
        )
    if not comments:
        return None
    return {
        "platform": "google",
        "facility_slug": facility_slug,
        "post": {
            "external_id": place_id,
            "url": url,
            "author_name": (place.get("displayName") or {}).get("text", ""),
            "caption": "Reviews shown on Google Maps",
            "match_method": "google_place_id",
        },
        "comments": comments,
    }
