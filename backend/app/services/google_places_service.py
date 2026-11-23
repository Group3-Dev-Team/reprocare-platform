

import httpx

from app.config import settings

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryTypeDisplayName",
        "places.googleMapsUri",
        "nextPageToken",
    ]
)
GOOGLE_PAGE_SIZE = 20  # API maximum per response


class PlacesNotConfigured(Exception):
    pass


class PlacesError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.google_places_api_key)


def _shape(place: dict) -> dict:
    location = place.get("location") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text", ""),
        "address": place.get("formattedAddress", ""),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "type_label": (place.get("primaryTypeDisplayName") or {}).get("text", ""),
        "google_maps_uri": place.get("googleMapsUri", ""),
    }


def text_search(query: str, max_results: int = 40, page_token: str | None = None, client: httpx.Client | None = None) -> dict:
    """Return up to `max_results` (≤ 40) places plus a token for the next page, if Google offers one."""
    if not is_configured():
        raise PlacesNotConfigured("Google Places is not configured on this server.")
    max_results = max(1, min(max_results, 40))
    headers = {"X-Goog-Api-Key": settings.google_places_api_key, "X-Goog-FieldMask": FIELD_MASK}
    results: list[dict] = []
    token = page_token
    own_client = client is None
    client = client or httpx.Client(timeout=10)
    try:
        while len(results) < max_results:
            body = {
                "textQuery": query,
                "pageSize": min(GOOGLE_PAGE_SIZE, max_results - len(results)),
                "regionCode": "KE",
                "languageCode": "en",
            }
            if token:
                body["pageToken"] = token
            response = client.post(TEXT_SEARCH_URL, json=body, headers=headers)
            if response.status_code != 200:
                message = response.json().get("error", {}).get("message", response.text) if response.content else response.reason_phrase
                raise PlacesError(f"Google Places returned {response.status_code}: {message}")
            data = response.json()
            results.extend(_shape(p) for p in data.get("places", []))
            token = data.get("nextPageToken")
            if not token:
                break
    except httpx.HTTPError as exc:
        raise PlacesError(f"Could not reach Google Places: {exc}") from exc
    finally:
        if own_client:
            client.close()
    return {"results": results[:max_results], "next_page_token": token, "attribution": "Results from Google Maps"}
