"""Collection pipeline tests: parsing of each source, facility linking, staging (incl. legacy staging formats), import.

Source payloads below are TEST FIXTURES shaped like the documented responses of Google Places API (New),
the Apify TikTok actors used by the legacy scripts, and their staging files. They are never shown to patients.
"""

import http.server
import json
import os
import shutil
import threading
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import pytest

import bot_config
import facebook_collector as fb
import google_places as gp
import tiktok_collector as tt
from facebook_pages import page_slug

FIXTURES = Path(__file__).parent / "fixtures"

PLACE = {  # Place Details (New) shape
    "id": "ChIJfixtureFixturePlace01",
    "displayName": {"text": "Fixture General Hospital"},
    "formattedAddress": "Fixture Road, Westlands, Nairobi, Kenya",
    "addressComponents": [
        {"longText": "Nairobi", "types": ["locality", "political"]},
        {"longText": "Nairobi County", "types": ["administrative_area_level_1", "political"]},
    ],
    "location": {"latitude": -1.26, "longitude": 36.8},
    "types": ["hospital", "health", "point_of_interest"],
    "websiteUri": "https://fixture-hospital.example/",
    "nationalPhoneNumber": "020 0000000",
    "googleMapsUri": "https://maps.google.com/?cid=0000000000",
    "rating": 4.1,
    "userRatingCount": 1234,
    "regularOpeningHours": {"weekdayDescriptions": [f"{d}: Open 24 hours" for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]},
    "photos": [{"name": "places/ChIJfixtureFixturePlace01/photos/AAA", "widthPx": 800, "heightPx": 600, "authorAttributions": [{"displayName": "Fixture Photographer"}]}],
    "reviews": [
        {"name": "places/ChIJfixtureFixturePlace01/reviews/R1", "rating": 2, "text": {"text": "Test fixture review: long wait."}, "originalText": {"text": "Test fixture review: long wait."}, "publishTime": "2026-10-01T08:00:00Z", "authorAttribution": {"displayName": "Fixture Reviewer"}},
        {"name": "places/ChIJfixtureFixturePlace01/reviews/R2", "rating": 5, "text": {"text": "Test fixture review: excellent maternity care."}, "publishTime": "2026-09-01T08:00:00Z", "authorAttribution": {"displayName": "Another Reviewer"}},
    ],
}


# --------------------------------------------------------------------------- parsing

def test_facebook_aria_label_parsing():
    now = datetime(2026, 11, 19, tzinfo=timezone.utc)
    meta = fb.parse_aria_label("Comment by Jane Wanjiku Doe 3 weeks ago", now)
    assert meta["author"] == "Jane Wanjiku Doe" and meta["is_reply"] is False
    assert meta["published_at"].startswith("2026-10-29")
    assert fb.parse_aria_label("Reply by Aga Khan University Hospital an hour ago", now)["is_reply"] is True
    assert fb.parse_aria_label("Comment by Someone", now) == {"author": "Someone", "is_reply": False, "published_at": None}
    assert fb.parse_aria_label("", now)["author"] == ""


def test_facebook_urls_and_official_posts():
    assert fb.clean_post_url("https://www.facebook.com/akuhnairobi/posts/pfbid0abc?__cft__=x&ref=y") == "https://web.facebook.com/akuhnairobi/posts/pfbid0abc"
    assert fb.clean_post_url("https://example.com/akuhnairobi/posts/1") is None
    posts = [
        "https://web.facebook.com/akuhnairobi/posts/pfbidA",
        "https://web.facebook.com/someoneelse/posts/pfbidB",
        "https://web.facebook.com/akuhnairobi/posts/pfbidA",
        "https://web.facebook.com/kenya-national-hospital-222808627792716/posts/pfbidC",
    ]
    assert fb.official_posts(posts, "akuhnairobi") == ["https://web.facebook.com/akuhnairobi/posts/pfbidA"]
    assert page_slug("https://www.facebook.com/kenyatta-national-hospital-222808627792716") == "kenyattanationalhospital"  # legacy alias
    assert page_slug("https://www.facebook.com/sharer/sharer.php?u=x") is None


@pytest.fixture()
def fixture_server():
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.mark.skipif(not (bot_config.BROWSER_PATH or shutil.which("google-chrome") or os.path.isdir(os.path.expanduser("~/.cache/ms-playwright"))), reason="no browser available")
def test_facebook_collector_extraction_with_playwright(fixture_server, monkeypatch):
    """Runs the legacy extraction logic in a real browser against a local imitation of a post page."""
    if not bot_config.BROWSER_PATH and shutil.which("google-chrome"):
        monkeypatch.setattr(bot_config, "BROWSER_PATH", shutil.which("google-chrome"))
    result = fb.collect_post(f"{fixture_server}/facebook_post.html", page_name="Fixture General Hospital")
    assert result["status"] == "ok"
    assert result["post"]["caption"].startswith("Test fixture post")
    assert result["post"]["thumbnail_url"] == "https://scontent.example/fixture.jpg"
    texts = [c["text"] for c in result["comments"]]
    assert texts == [
        "Test fixture: the maternity nurses were very kind to me.",
        "Test fixture: thank you, we are glad you were well cared for.",
        "Test fixture: do you take SHA for scans?",
    ]  # mismatched text skipped, duplicate skipped
    first, reply, third = result["comments"]
    assert first["author_name"] == "Amina Fixture" and first["published_at_approximate"]
    assert reply["author_is_facility"] and reply["parent_external_id"] == first["external_id"]
    assert third["parent_external_id"] is None


def test_tiktok_parsing():
    search = {"url": "https://www.tiktok.com/@fixturecreator/video/7300000000000000001?is_from_webapp=1", "desc": "Delivered my baby at Fixture General Hospital, Nairobi! #fixture", "author": {"uniqueId": "fixturecreator"}, "video": {"cover": "https://p16.example/cover.jpg"}, "createTime": 1760000000}
    assert tt.video_url(search) == "https://www.tiktok.com/@fixturecreator/video/7300000000000000001"
    assert tt.relevant(search, "Fixture General Hospital")
    assert not tt.relevant({"desc": "general hospital vibes"}, "Fixture General Hospital")
    ctx = tt.video_context(search, tt.video_url(search))
    assert ctx["external_id"] == "7300000000000000001" and ctx["author_name"] == "@fixturecreator"
    assert ctx["thumbnail_url"] == "https://p16.example/cover.jpg" and ctx["published_at"].startswith("2025-10-09")

    dataset = [
        {"cid": "7300000000000000101", "text": "Test fixture: nurses were rude", "createTimeISO": "2026-10-10T10:00:00.000Z", "diggCount": 12, "uniqueId": "fixture_user", "videoWebUrl": "https://www.tiktok.com/@fixturecreator/video/7300000000000000001",
         "replies": [{"cid": "7300000000000000102", "text": "Test fixture: same experience", "createTimeISO": "2026-10-11T10:00:00.000Z", "uniqueId": "fixture_two", "videoWebUrl": "https://www.tiktok.com/@fixturecreator/video/7300000000000000001"}]},
        {"cid": "7300000000000000103", "text": "Test fixture other video", "videoWebUrl": "https://www.tiktok.com/@x/video/7999999999999999999"},
        {"cid": "notnumeric", "text": "bad"},
        {"cid": "7300000000000000104", "text": "   "},
    ]
    comments = tt.comments_from_dataset(dataset, "7300000000000000001")
    assert [c["external_id"] for c in comments] == ["7300000000000000101", "7300000000000000102"]
    assert comments[1]["parent_external_id"] == "7300000000000000101" and comments[0]["like_count"] == 12
    assert comments[0]["author_name"] == "@fixture_user"


def test_google_shaping():
    assert gp.facility_type(PLACE) == "hospital"
    assert gp.facility_type({"displayName": {"text": "Fixture Maternity Home"}, "types": []}) == "maternity_home"
    assert gp.facility_type({"displayName": {"text": "Fixture Pizza"}, "types": ["restaurant"]}) is None
    assert gp.town_and_county(PLACE) == ("Nairobi", "Nairobi")
    hours = gp.opening_hours(PLACE)
    assert hours["open_24_hours"] and hours["open_weekends"] and hours["weekday_hours"] == "Open 24 hours"
    assert gp.photo_refs(PLACE)[0]["attributions"] == ["Fixture Photographer"]
    batch = gp.reviews_batch(PLACE, "fixture-general-hospital")
    assert batch["post"]["external_id"] == PLACE["id"] and [c["source_rating"] for c in batch["comments"]] == [2, 5]


def test_places_cache_daily_limit(monkeypatch):
    import places_cache

    monkeypatch.setattr(places_cache, "DAILY_LIMIT", 2)
    calls = []
    fetch = lambda: calls.append(1) or {"ok": len(calls)}  # noqa: E731
    assert places_cache.cached_request("k1", fetch) == {"ok": 1}
    assert places_cache.cached_request("k1", fetch) == {"ok": 1}  # cached: no new billed call
    places_cache.cached_request("k2", fetch)
    with pytest.raises(places_cache.DailyLimitReached):
        places_cache.cached_request("k3", fetch)
    assert len(calls) == 2


def test_missing_credentials_fail_clearly():
    with pytest.raises(gp.PlacesUnavailable, match="GOOGLE_PLACES_API_KEY"):
        gp._get("https://places.googleapis.com/v1/places/x", "id")
    with pytest.raises(tt.ApifyUnavailable, match="APIFY_API_TOKEN"):
        tt.actor_run(tt.SEARCH_ACTOR, {})


# --------------------------------------------------------------------------- database: facilities + import

def test_upsert_from_place_no_duplicates_and_preserves_edits(db):
    from facilities import upsert_from_place
    from app.models import Facility, FacilityExternalProfile

    facility, outcome = upsert_from_place(db, PLACE)
    db.commit()
    assert outcome == "created" and facility.is_demo is False and facility.county == "Nairobi" and facility.open_24_hours
    facility.phone = "0700 000 000 (edited by staff)"
    db.commit()
    again, outcome = upsert_from_place(db, {**PLACE, "nationalPhoneNumber": "999"})
    db.commit()
    assert outcome == "updated" and again.id == facility.id and again.phone.endswith("(edited by staff)")
    assert db.query(Facility).filter_by(external_id=PLACE["id"]).count() == 1
    profile = db.query(FacilityExternalProfile).filter_by(facility_id=facility.id, platform="google").one()
    assert profile.rating == 4.1 and profile.rating_count == 1234 and profile.photos[0]["name"].endswith("/AAA")
    _, outcome = upsert_from_place(db, {"id": "ChIJfixtureNotHealth00", "displayName": {"text": "Fixture Cafe"}, "types": ["cafe"], "addressComponents": PLACE["addressComponents"]})
    assert outcome.startswith("skipped")


def test_staging_import_end_to_end_including_file_b_formats(db):
    import importer
    import staging
    from app.models import ExternalComment, ExternalPost, Facility

    slug = db.query(Facility).filter_by(external_id=PLACE["id"]).one().slug

    # New-format batches from each collector
    staging.write_batch(gp.reviews_batch(PLACE, slug))
    staging.write_batch(
        {"platform": "facebook", "facility_slug": slug, "post": {"external_id": staging.facebook_post_id("https://web.facebook.com/fixturegh/posts/pfbidNEW"), "url": "https://web.facebook.com/fixturegh/posts/pfbidNEW", "caption": "Test fixture caption", "match_method": "facility_page_post"},
         "comments": [{"external_id": "fx-new-1", "author_name": "Fixture Person", "text": "Test fixture comment about the ward"}]}
    )

    # legacy staging formats, exactly as those scripts wrote them
    legacy_fb = Path(bot_config.LEGACY_FACEBOOK_DIR)
    legacy_fb.mkdir(parents=True, exist_ok=True)
    (legacy_fb / "fixture_general_hospital_0123456789ab.json").write_text(json.dumps([
        {"id": "x", "platform": "facebook", "facility": "fixture general  HOSPITAL", "text": "Test fixture legacy FB comment", "source_url": "https://web.facebook.com/fixturegh/posts/pfbidOLD", "classification": "unverified_comment_candidate", "collected_at": "2026-11-01T00:00:00+00:00"},
        {"id": "y", "platform": "facebook", "facility": "Unknown Fixture Clinic", "text": "Test fixture unresolvable", "source_url": "https://web.facebook.com/other/posts/pfbidZZ", "collected_at": "2026-11-01T00:00:00+00:00"},
    ]))
    Path(bot_config.LEGACY_TIKTOK_DIR).mkdir(parents=True, exist_ok=True)
    (Path(bot_config.LEGACY_TIKTOK_DIR) / "7300000000000000009.json").write_text(json.dumps({
        "facility": "Fixture General Hospital", "video_url": "https://www.tiktok.com/@fx/video/7300000000000000009", "platform": "tiktok",
        "records": [{"cid": "7300000000000000901", "text": "Test fixture legacy TikTok comment", "createTimeISO": "2026-10-01T00:00:00Z", "videoWebUrl": "https://www.tiktok.com/@fx/video/7300000000000000009"}],
    }))
    Path(bot_config.LEGACY_GOOGLE_FILE).write_text(json.dumps([
        {"reviewId": "fx-apify-1", "placeId": PLACE["id"], "text": "Test fixture Apify Google review", "stars": 3, "url": "https://www.google.com/maps/place/fixture", "name": "Fixture Name"},
    ]))

    batches = [b for _, b in staging.read_batches()] + staging.legacy_batches()
    assert len(batches) == 6
    result = importer.import_direct(batches, "test")
    assert result["imported"] == 5 and len(result["unresolved"]) == 1 and "Unknown Fixture Clinic" in result["unresolved"][0]
    assert result["comments_created"] == 6

    again = importer.import_direct(batches, "test")
    assert again["comments_created"] == 0 and again["comments_skipped"] == 6

    facility = db.query(Facility).filter_by(slug=slug).one()
    by_platform = {p: db.query(ExternalComment).filter_by(facility_id=facility.id, platform=p).count() for p in ("facebook", "tiktok", "google")}
    assert by_platform == {"facebook": 2, "tiktok": 1, "google": 3}
    assert db.query(ExternalPost).filter_by(facility_id=None).count() == 0  # unresolved data is not stored at all


def test_cli_preview_modes_make_no_calls(capsys):
    import reprocare_bot

    reprocare_bot.main(["discover"])
    reprocare_bot.main(["tiktok", "--all"])
    out = capsys.readouterr().out
    assert "PREVIEW ONLY" in out and out.count("PREVIEW ONLY") == 2
    reprocare_bot.main(["google", "--all"])  # no key: each facility run is recorded as failed, nothing invented
    reprocare_bot.main(["report"])
    assert "ReproCare ratings: unaffected" in capsys.readouterr().out


# --------------------------------------------------------------------------- Apify endpoint compatibility (no network)

class _Resp:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def read(self, *a):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code):
    from urllib.error import HTTPError

    return HTTPError("https://api.apify.com/x", code, "fixture", {}, None)


@pytest.fixture()
def fake_apify(monkeypatch):
    calls = []

    def install(*responses):
        queue = list(responses)

        def fake_urlopen(request, timeout):
            calls.append({"url": request.full_url, "timeout": timeout, "auth": request.get_header("Authorization"), "body": json.loads(request.data)})
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return _Resp(item)

        monkeypatch.setattr(tt, "urlopen", fake_urlopen)
        monkeypatch.setattr(tt, "apify_token", lambda: "fixture-token-not-real")
        return calls

    return install


def test_apify_uses_file_b_endpoint_first(fake_apify, capsys):
    calls = fake_apify([{"id": 1}])
    assert tt.actor_run(tt.SEARCH_ACTOR, {"search": ["x"]}) == [{"id": 1}]
    assert calls[0]["url"] == "https://api.apify.com/v2/actors/epctex~tiktok-search-scraper/run-sync-get-dataset-items?timeout=120"
    assert calls[0]["timeout"] == 135 and calls[0]["body"] == {"search": ["x"]}
    out = capsys.readouterr().out
    assert "/v2/actors/epctex~tiktok-search-scraper/run-sync-get-dataset-items" in out and "fixture-token-not-real" not in out


def test_apify_falls_back_to_acts_only_on_404(fake_apify, capsys):
    calls = fake_apify(_http_error(404), [{"cid": "1"}])
    assert tt.actor_run(tt.COMMENTS_ACTOR, {"postURLs": ["u"]}) == [{"cid": "1"}]
    assert [c["url"].split("/v2/")[1].split("/")[0] for c in calls] == ["actors", "acts"]
    assert calls[1]["body"] == calls[0]["body"] and calls[1]["auth"] == "Bearer fixture-token-not-real"
    assert "fixture-token-not-real" not in capsys.readouterr().out


@pytest.mark.parametrize("code", [401, 403, 429, 500, 502, 503])
def test_apify_does_not_retry_other_errors(fake_apify, code):
    calls = fake_apify(_http_error(code), [{"never": "used"}])
    with pytest.raises(tt.ApifyUnavailable, match=f"HTTP {code}"):
        tt.actor_run(tt.SEARCH_ACTOR, {})
    assert len(calls) == 1


def test_apify_404_on_both_endpoints_is_reported(fake_apify):
    calls = fake_apify(_http_error(404), _http_error(404))
    with pytest.raises(tt.ApifyUnavailable, match="HTTP 404"):
        tt.actor_run(tt.SEARCH_ACTOR, {})
    assert len(calls) == 2


def test_apify_non_list_result_rejected(fake_apify):
    fake_apify({"error": "not a list"})
    with pytest.raises(tt.ApifyUnavailable, match="Unexpected"):
        tt.actor_run(tt.SEARCH_ACTOR, {})


def test_facebook_login_wall_is_recorded_without_prompting(db, monkeypatch, capsys):
    import facebook_collector
    import facebook_pages
    import reprocare_bot
    from app.models import ExternalCollectionRun, Facility

    slug = db.query(Facility).filter_by(external_id=PLACE["id"]).one().slug
    monkeypatch.setattr(facebook_pages, "find_official_page", lambda name, site: ("https://web.facebook.com/fixturegh", "fixturegh", "official_website"))
    monkeypatch.setattr(facebook_collector, "find_posts", lambda url, limit: ([], "", True))
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)  # unattended run
    reprocare_bot.main(["facebook", "--facility", slug])
    assert "requires sign-in" in capsys.readouterr().out
    run = db.query(ExternalCollectionRun).filter_by(platform="facebook").order_by(ExternalCollectionRun.id.desc()).first()
    assert run.status == "failed" and "facebook-login" in run.message
