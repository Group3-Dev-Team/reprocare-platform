"""Live facility discovery with Google Places API (New) — Text Search.

* Uses a narrow field mask: only the fields the interface shows are requested (and billed).
* One Text Search response holds at most 20 places. To fill a 40-result page we request a second page
  with `nextPageToken`. Google returns at most 60 places for one query in total.
* Results are shown live with Google attribution and are NOT copied into the ReproCare database.
  Google's terms allow storing the place ID; other content must not be cached beyond what the terms permit.
* The API key stays on the server (GOOGLE_PLACES_API_KEY). The browser never sees it.
"""

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


def written_reviews(place_id: str, client: httpx.Client | None = None) -> dict:
    """Fetch live attributed reviews for a stored Place ID without caching them."""
    from urllib.parse import quote, urlsplit

    if not is_configured():
        raise PlacesNotConfigured("Google Places is not configured on this server.")

    def google_link(url):
        if not isinstance(url, str):
            return None
        try:
            source = urlsplit(url)
        except ValueError:
            return None
        host = source.hostname or ""
        if source.scheme == "https" and not source.username and not source.password and (
            host == "google.com" or host.endswith(".google.com")
            or host.endswith(".googleusercontent.com") or host == "maps.app.goo.gl"
        ):
            return url
        return None

    headers = {"X-Goog-Api-Key": settings.google_places_api_key, "X-Goog-FieldMask": "reviews,attributions"}
    url = "https://places.googleapis.com/v1/places/" + quote(place_id, safe="")
    own_client = client is None
    client = client or httpx.Client(timeout=12)
    try:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            try:
                error = response.json().get("error") or {}
                codes = [item.get("reason") for item in error.get("details", []) if isinstance(item, dict)]
            except ValueError:
                codes = []
            reason = next((code for code in codes if code in {
                "API_KEY_INVALID", "API_KEY_SERVICE_BLOCKED", "API_KEY_HTTP_REFERRER_BLOCKED",
                "API_KEY_IP_ADDRESS_BLOCKED", "SERVICE_DISABLED", "BILLING_DISABLED",
                "RATE_LIMIT_EXCEEDED", "QUOTA_EXCEEDED",
            }), None)
            descriptions = {403: "permissions, key restrictions, or billing", 404: "stored place ID not found",
                            429: "quota or rate limit reached"}
            detail = descriptions.get(response.status_code, "request failed")
            suffix = f"; {reason}" if reason else ""
            raise PlacesError(f"Google Place Details returned HTTP {response.status_code} ({detail}{suffix}).")
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PlacesError(f"Google Place Details could not be read ({type(exc).__name__}).") from exc
    finally:
        if own_client:
            client.close()

    returned = data.get("reviews") or []
    reviews = []
    for review in returned:
        author = review.get("authorAttribution") or {}
        text = (review.get("text") or review.get("originalText") or {}).get("text")
        source = google_link(review.get("googleMapsUri"))
        if not (text and source and author.get("displayName")):
            continue
        reviews.append({
            "text": text, "rating": review.get("rating"), "published_at": review.get("publishTime"),
            "source": source, "author": author["displayName"], "author_url": google_link(author.get("uri")),
            "author_photo": google_link(author.get("photoUri")),
        })
    return {
        "reviews": reviews, "returned_count": len(returned),
        "attributions": [{"provider": item["provider"], "url": google_link(item.get("providerUri"))}
                         for item in (data.get("attributions") or []) if item.get("provider")],
    }
