"""Google Places service, tested against a mocked HTTP transport (no real key or network needed)."""

import httpx
import pytest

from app.config import settings
from app.services import google_places_service as places


def test_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "google_places_api_key", "")
    assert client.get("/api/places/status").json() == {"configured": False}
    assert client.get("/api/places/search?q=clinic").status_code == 503


def test_combines_two_google_pages_into_40(monkeypatch):
    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    calls = []

    def handler(request: httpx.Request):
        body = request.read().decode()
        calls.append((request.headers["X-Goog-FieldMask"], body))
        page = 2 if "pageToken" in body else 1
        places_json = [{"id": f"p{page}-{i}", "displayName": {"text": f"Clinic {page}-{i}"}, "location": {"latitude": -1.0, "longitude": 36.0}} for i in range(20)]
        return httpx.Response(200, json={"places": places_json, "nextPageToken": f"token-{page}"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = places.text_search("maternity Nakuru", max_results=40, client=client)
    assert len(result["results"]) == 40 and len(calls) == 2
    assert "places.id" in calls[0][0] and "reviews" not in calls[0][0]  # narrow field mask
    assert result["next_page_token"] == "token-2"


def test_google_error_is_reported(monkeypatch):
    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": {"message": "API key not valid"}})))
    with pytest.raises(places.PlacesError, match="API key not valid"):
        places.text_search("clinic", client=client)


def test_written_reviews_preserve_required_attribution(monkeypatch):
    import httpx
    from app.services import google_places_service as places

    monkeypatch.setattr(places.settings, "google_places_api_key", "test-only")

    def handler(request):
        assert request.headers["X-Goog-FieldMask"] == "reviews,attributions"
        return httpx.Response(200, json={"reviews": [
            {"text": {"text": "Fixture review"}, "rating": 4,
             "googleMapsUri": "https://maps.google.com/reviews/example",
             "authorAttribution": {"displayName": "Fixture Reviewer", "uri": "https://www.google.com/maps/contrib/example"}},
            {"rating": 5},
        ]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = places.written_reviews("fixture-place", client)
    assert result["returned_count"] == 2
    assert len(result["reviews"]) == 1
    assert result["reviews"][0]["author"] == "Fixture Reviewer"
    assert result["reviews"][0]["source"] == "https://maps.google.com/reviews/example"


def test_written_reviews_report_quota_without_echoing_provider_message(monkeypatch):
    import httpx
    import pytest
    from app.services import google_places_service as places

    monkeypatch.setattr(places.settings, "google_places_api_key", "test-only")

    def handler(request):
        return httpx.Response(429, json={"error": {"message": "private provider response",
                              "details": [{"reason": "QUOTA_EXCEEDED"}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(places.PlacesError, match="HTTP 429.*QUOTA_EXCEEDED") as error:
            places.written_reviews("fixture-place", client)
    assert "private provider" not in str(error.value)
