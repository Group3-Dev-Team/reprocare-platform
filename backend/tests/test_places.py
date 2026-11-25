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


def test_live_google_requests_are_limited_per_client_and_per_day(client, make_facility, monkeypatch):
    """Regression: the public live endpoints had no request limit, so repeated clicks or a script could run up
    unbounded Google charges. Each client and the server as a whole now have limits; refusals never call Google."""
    from app.database.session import SessionLocal
    from app.services.external_feedback_service import upsert_profile
    from app.models import Facility

    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    facility = make_facility(name="Fixture Live Reviews Hospital", is_demo=False)
    with SessionLocal() as db:
        upsert_profile(db, db.get(Facility, facility.id), "google", "ChIJfixtureLiveReviews01", url="", match_method="google_place_id")
        db.commit()
    calls = []
    monkeypatch.setattr(places, "written_reviews", lambda place_id, client=None: calls.append(place_id) or {"reviews": [], "returned_count": 0, "attributions": []})
    places.reset_live_budget()
    monkeypatch.setattr(places, "LIVE_REQUESTS_PER_CLIENT", 3)
    url = f"/api/places/facilities/{facility.slug}/reviews"
    assert [client.get(url).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert calls == ["ChIJfixtureLiveReviews01"] * 3
    assert "Too many" in client.get(url).json()["detail"]

    places.reset_live_budget()
    monkeypatch.setattr(settings, "google_places_live_daily_limit", 2)
    assert [client.get(url).status_code for _ in range(3)] == [200, 200, 429]
    assert len(calls) == 5
    searches = []
    monkeypatch.setattr(places, "text_search", lambda *a, **k: searches.append(a) or {"results": []})
    assert client.get("/api/places/search?q=clinic").status_code == 429 and searches == []
    places.reset_live_budget()
    # a missing place id is answered without spending anything
    other = make_facility(name="Fixture No Place Id", is_demo=False)
    assert client.get(f"/api/places/facilities/{other.slug}/reviews").status_code == 404 and len(calls) == 5


def test_live_search_shows_ratings_and_points_linked_places_to_the_listing(client, make_facility, monkeypatch):
    from app.database.session import SessionLocal
    from app.models import FacilityExternalProfile

    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    places.reset_live_budget()
    listed = make_facility(name="Livefixture Listed Clinic")
    with SessionLocal() as db:
        db.add(FacilityExternalProfile(facility_id=listed.id, platform="google", external_id="ChIJlivefixtureListed01"))
        db.commit()
    seen = []

    def fake_search(q, max_results=40, page_token=None, client=None):
        seen.append(q)
        return {"results": [
            {"place_id": "ChIJlivefixtureListed01", "name": "Listed", "rating": 4.1, "rating_count": 30},
            {"place_id": "ChIJlivefixtureOther001", "name": "Other", "rating": None, "rating_count": None},
        ], "next_page_token": None, "attribution": "Results from Google Maps"}

    monkeypatch.setattr(places, "text_search", fake_search)
    reply = client.get("/api/places/search?q=clinic")
    assert reply.status_code == 200 and reply.headers["cache-control"] == "no-store"
    by_id = {p["place_id"]: p for p in reply.json()["results"]}
    assert by_id["ChIJlivefixtureListed01"]["facility_slug"] == listed.slug
    assert by_id["ChIJlivefixtureOther001"]["facility_slug"] is None
    # A linked place opens the stored listing without calling Google.
    monkeypatch.setattr(places, "place_details", lambda *a, **k: pytest.fail("Google should not be called"))
    assert client.get("/api/places/place/ChIJlivefixtureListed01").json() == {"place_id": "ChIJlivefixtureListed01", "facility_slug": listed.slug}


def test_rating_fields_are_requested_and_returned():
    assert "places.rating" in places.FIELD_MASK and "places.userRatingCount" in places.FIELD_MASK
    assert places._shape({"id": "x", "rating": 4.5, "userRatingCount": 12})["rating_count"] == 12


def test_live_place_details_and_reviews_use_the_place_id(client, monkeypatch):
    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    places.reset_live_budget()
    paths = []

    def handler(request):
        paths.append((request.url.path, request.headers["X-Goog-FieldMask"]))
        return httpx.Response(200, json={"id": "ChIJlivefixtureOther001", "displayName": {"text": "Fixture Live Clinic"},
                                         "rating": 3.9, "userRatingCount": 8, "websiteUri": "javascript:alert(1)"})

    mock = httpx.Client(transport=httpx.MockTransport(handler))
    details = places.place_details("ChIJlivefixtureOther001", client=mock)
    assert details["name"] == "Fixture Live Clinic" and details["rating"] == 3.9 and details["website"] == ""
    assert paths[0][0] == "/v1/places/ChIJlivefixtureOther001" and "reviews" not in paths[0][1]
    assert client.get("/api/places/place/bad id!").status_code == 422
    monkeypatch.setattr(places, "written_reviews", lambda pid, client=None: {"reviews": [], "returned_count": 0, "attributions": [], "pid": pid})
    assert client.get("/api/places/place/ChIJlivefixtureOther001/reviews").json()["pid"] == "ChIJlivefixtureOther001"


def test_photos_are_off_by_default_and_never_call_google(client, make_facility, monkeypatch):
    from app.database.session import SessionLocal
    from app.models import FacilityExternalProfile

    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    places.reset_live_budget()
    monkeypatch.setattr(places, "place_photo", lambda *a, **k: pytest.fail("Google should not be called"))
    f = make_facility(name="Photofixture Clinic")
    unlinked = make_facility(name="Photofixture Unlinked")
    with SessionLocal() as db:
        db.add(FacilityExternalProfile(facility_id=f.id, platform="google", external_id="ChIJphotofixture0001"))
        db.commit()
    assert client.get(f"/api/places/facilities/{f.slug}/photo").status_code == 429
    assert client.get(f"/api/places/facilities/{unlinked.slug}/photo").status_code == 404
    listing = client.get("/api/facilities?q=Photofixture").json()["items"]
    assert {i["name"]: i["has_google_place"] for i in listing} == {"Photofixture Clinic": True, "Photofixture Unlinked": False}
    assert client.get(f"/api/facilities/{f.slug}").json()["has_google_place"] is True


def test_photo_is_returned_with_author_attribution_within_the_daily_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    monkeypatch.setattr(settings, "google_places_photo_daily_limit", 1)
    places.reset_live_budget()

    def handler(request):
        if request.url.path.endswith("/media"):
            assert request.url.params["skipHttpRedirect"] == "true" and request.url.params["maxWidthPx"] == "480"
            return httpx.Response(200, json={"photoUri": "https://lh3.googleusercontent.com/fixture"})
        assert request.headers["X-Goog-FieldMask"] == "photos"
        return httpx.Response(200, json={"photos": [{"name": "places/ChIJphotofixture0001/photos/abc", "widthPx": 800, "heightPx": 600,
                                                     "authorAttributions": [{"displayName": "Fixture Photographer", "uri": "https://maps.google.com/contrib/1"}]}]})

    mock = httpx.Client(transport=httpx.MockTransport(handler))
    photo = places.place_photo("ChIJphotofixture0001", client=mock)
    assert photo["photo_uri"].startswith("https://lh3.googleusercontent.com/")
    assert photo["authors"] == [{"name": "Fixture Photographer", "url": "https://maps.google.com/contrib/1"}]
    # A photo name belonging to another place is rejected.
    other = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"photos": [{"name": "places/ELSEWHERE/photos/x"}]})))
    assert places.place_photo("ChIJphotofixture0001", client=other) is None
    monkeypatch.setattr(places, "place_photo", lambda pid, max_width=480: {"photo_uri": "https://lh3.googleusercontent.com/x", "authors": []})
    assert client.get("/api/places/place/ChIJphotofixture0001/photo").status_code == 200
    assert client.get("/api/places/place/ChIJphotofixture0001/photo").status_code == 429  # cap of 1 reached


def test_facility_summary_gives_live_rating_and_photo_only_within_caps(client, make_facility, monkeypatch):
    from app.database.session import SessionLocal
    from app.models import FacilityExternalProfile

    monkeypatch.setattr(settings, "google_places_api_key", "fake-key")
    monkeypatch.setattr(settings, "google_places_photo_daily_limit", 1)
    monkeypatch.setattr(settings, "google_places_live_daily_limit", 2)
    places.reset_live_budget()
    f = make_facility(name="Summaryfixture Clinic")
    with SessionLocal() as db:
        db.add(FacilityExternalProfile(facility_id=f.id, platform="google", external_id="ChIJsummaryfixture01"))
        db.commit()
    calls = []

    def fake_summary(place_id, with_photo, max_width=480, client=None):
        calls.append((place_id, with_photo))
        return {"rating": 4.2, "rating_count": 9, "google_maps_uri": "", "photo": None, "attribution": "Google Maps"}

    monkeypatch.setattr(places, "place_summary", fake_summary)
    first = client.get(f"/api/places/facilities/{f.slug}/summary")
    assert first.status_code == 200 and first.json()["rating"] == 4.2 and first.headers["cache-control"] == "no-store"
    client.get(f"/api/places/facilities/{f.slug}/summary")
    assert calls == [("ChIJsummaryfixture01", True), ("ChIJsummaryfixture01", False)]  # photo cap of 1 reached
    assert client.get(f"/api/places/facilities/{f.slug}/summary").status_code == 429  # daily cap of 2 reached
    assert len(calls) == 2


def test_place_summary_requests_rating_and_photo_fields():
    masks = []

    def handler(request):
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"photoUri": "https://lh3.googleusercontent.com/s"})
        masks.append(request.headers["X-Goog-FieldMask"])
        return httpx.Response(200, json={"rating": 4.0, "userRatingCount": 3, "photos": [{"name": "places/ChIJsummaryfixture01/photos/a"}]})

    settings_key = settings.google_places_api_key
    settings.google_places_api_key = "fake-key"
    try:
        out = places.place_summary("ChIJsummaryfixture01", True, client=httpx.Client(transport=httpx.MockTransport(handler)))
    finally:
        settings.google_places_api_key = settings_key
    assert masks == ["rating,userRatingCount,googleMapsUri,photos"] and "reviews" not in masks[0]
    assert out["rating"] == 4.0 and out["photo"]["photo_uri"].startswith("https://lh3.googleusercontent.com/")
