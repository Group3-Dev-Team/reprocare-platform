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
    """Runs comment and reply extraction in a browser against an offline fixture."""
    if not bot_config.BROWSER_PATH and shutil.which("google-chrome"):
        monkeypatch.setattr(bot_config, "BROWSER_PATH", shutil.which("google-chrome"))
    result = fb.collect_post(f"{fixture_server}/facebook_post.html", page_name="Fixture General Hospital")
    assert result["status"] == "ok"
    assert result["post"]["caption"].startswith("Test fixture post")
    assert result["post"]["thumbnail_url"] == "https://scontent.example/fixture.jpg"
    texts = [c["text"] for c in result["comments"]]
    assert texts == [
        "Test fixture: the maternity nurses were very kind to me.",
        "Test fixture: do you take SHA for scans?",
        "Test fixture: please check the listing.",
        "Test fixture: thank you, we are glad you were well cared for.",
    ]
    first, second, nested, reply = result["comments"]
    assert first["author_name"] == "Amina Fixture" and first["published_at_approximate"]
    assert reply["author_is_facility"] and reply["parent_external_id"] == first["external_id"]
    assert second["parent_external_id"] is None and nested["parent_external_id"] == second["external_id"]
    assert result["unlinked_replies"] == 1


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


def test_facebook_collection_stages_empty_posts_and_preserves_prior_capture(db, monkeypatch, tmp_path):
    import facebook_pages
    import reprocare_bot
    import staging
    from app.models import ExternalCollectionRun, ExternalComment, ExternalPost, Facility

    slug = "fixture-facebook-collection"
    db.add(Facility(slug=slug, name="Fixture Facebook Collection", facility_type="hospital", town="Nairobi", county="Nairobi"))
    db.commit()
    first, empty, unavailable = [f"https://web.facebook.com/fixturecollection/posts/{i}" for i in range(3)]
    original = {
        "platform": "facebook",
        "facility_slug": slug,
        "post": {"external_id": staging.facebook_post_id(first), "url": first, "caption": "Original context"},
        "comments": [{"external_id": "prior-parent", "text": "Older staged fixture comment"}],
    }
    monkeypatch.setattr(staging, "BATCHES", tmp_path)
    staging.write_batch(original)
    monkeypatch.setattr(facebook_pages, "find_official_page", lambda name, site: ("https://web.facebook.com/fixturecollection", "fixturecollection", "official_website"))
    monkeypatch.setattr(fb, "find_posts", lambda url, limit: ([first, empty, unavailable], "Fixture Facebook Collection", False))
    responses = {
        first: {"post": {}, "comments": [{"external_id": "later-child", "parent_external_id": "prior-parent", "text": "Fixture reply"}], "status": "ok"},
        empty: {"post": {}, "comments": [], "status": "no_comments_visible"},
        unavailable: {"post": {}, "comments": [], "status": "unreachable"},
    }
    monkeypatch.setattr(fb, "collect_post", lambda url, **kwargs: responses[url])
    reprocare_bot.main(["facebook", "--facility", slug])
    reprocare_bot.main(["facebook", "--facility", slug])

    staged = {batch["post"]["url"]: batch for _, batch in staging.read_batches()}
    assert set(staged) == {first, empty}
    assert staged[first]["post"]["caption"] == "Original context"
    assert [c["external_id"] for c in staged[first]["comments"]] == ["prior-parent", "later-child"]
    posts = db.query(ExternalPost).filter(ExternalPost.url.in_(responses)).all()
    assert {post.url for post in posts} == {first, empty}
    assert all(post.is_visible is False and post.facebook_scope is None for post in posts)
    comments = db.query(ExternalComment).filter(ExternalComment.post_id.in_([post.id for post in posts])).order_by(ExternalComment.id).all()
    assert [comment.external_id for comment in comments] == ["prior-parent", "later-child"]
    assert comments[1].parent_id == comments[0].id
    run = db.query(ExternalCollectionRun).filter_by(platform="facebook").order_by(ExternalCollectionRun.id.desc()).first()
    assert run.status == "succeeded" and "2 staged" in run.message and "unreachable (1)" in run.message


def test_tiktok_collection_keeps_the_stated_billing_bounds(fake_apify):
    """Regression: the collector requested 500 search results, every matching video, 500 comments and 100 replies,
    although the command promised at most 10 results, 2 videos, 10 comments and 2 replies (the legacy values)."""
    video = lambda n: {"url": f"https://www.tiktok.com/@fixturecreator/video/73000000000000000{n:02d}", "desc": f"Fixture General Hospital visit {n}"}  # noqa: E731
    calls = fake_apify([video(n) for n in range(1, 6)], [], [], [])  # one search term, then one comments run per kept video
    bundles = tt.collect_for_facility("Fixture General Hospital")
    searches = [c["body"] for c in calls if "search" in c["body"]]
    comments = [c["body"] for c in calls if "postURLs" in c["body"]]
    assert searches == [{"search": ["Fixture General Hospital"], "maxItems": 10, "endPage": 1, "sortType": "RELEVANCE"}]
    assert len(bundles) == len(comments) == 2  # 5 matching videos found, only 2 collected
    assert all(c["commentsPerPost"] == 10 and c["maxRepliesPerComment"] == 2 for c in comments)


def test_google_step_keeps_no_google_review_text(db, monkeypatch, tmp_path):
    """Google review text is shown live on the facility page (backend /places/.../reviews) and is not stored by the bot:
    the bot's Place Details request leaves out `reviews`, and nothing from Google reviews is staged or imported."""
    import places_cache
    import reprocare_bot
    import staging
    from app.models import ExternalComment, Facility, FacilityExternalProfile

    monkeypatch.setattr(places_cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(places_cache, "DATABASE", tmp_path / "places.sqlite3")
    monkeypatch.setattr(places_cache, "DAILY_LIMIT", 5)
    place_id = "ChIJfixtureNoReviewText1"
    facility = Facility(slug="fixture-no-review-text", name="Fixture No Review Text Hospital", facility_type="hospital",
                        town="Nairobi", county="Nairobi", is_demo=False)
    db.add(facility)
    db.flush()
    db.add(FacilityExternalProfile(facility_id=facility.id, platform="google", external_id=place_id, url=""))
    db.commit()
    masks = []

    def fake_get(url, field_mask):
        masks.append(field_mask)
        return {**PLACE, "id": place_id}  # even if Google sent reviews, the bot must not keep them

    monkeypatch.setattr(gp, "_get", fake_get)
    before = len(staging.read_batches())
    reprocare_bot.main(["google", "--facility", "fixture-no-review-text"])
    assert len(masks) == 1 and "reviews" not in masks[0].split(",")
    db.expire_all()
    assert db.query(ExternalComment).filter_by(facility_id=facility.id).count() == 0
    assert len(staging.read_batches()) == before
    profile = db.query(FacilityExternalProfile).filter_by(facility_id=facility.id, platform="google").one()
    assert profile.rating == 4.1 and profile.rating_count == 1234  # the rating summary is still refreshed


def test_facility_selection_targets_sources_profiles_and_stays_bounded(db):
    """Regression: `--all` took the first 630 facilities by name across every source, and the Google step also picked
    OpenStreetMap rows (external_id 'osm:…') that have no Google place id. Selection is now bounded and targetable."""
    import reprocare_bot
    from app.models import DataSource, Facility, FacilityExternalProfile

    source = DataSource(code="fixture_osm_source", name="Fixture OSM-like source", description="TEST FIXTURE", attribution="")
    db.add(source)
    db.flush()
    rows = {}
    for key, external_id in (("profile", "osm:node/9000000001"), ("placeholder", "osm:node/9000000002"), ("legacy", "ChIJfixtureLegacyPlaceId")):
        rows[key] = Facility(slug=f"fixture-select-{key}", name=f"Fixture Select {key.title()}", facility_type="clinic", town="Kisumu",
                             county="Kisumu", is_demo=False, source_id=source.id, external_id=external_id)
        db.add(rows[key])
    db.flush()
    db.add(FacilityExternalProfile(facility_id=rows["profile"].id, platform="google", external_id="ChIJfixtureSelectProfile1", url=""))
    db.commit()

    def slugs(**kw):
        return [f.slug for f in reprocare_bot.select_facilities(db, None, True, 10, source="fixture_osm_source", **kw)]

    assert slugs() == ["fixture-select-legacy", "fixture-select-placeholder", "fixture-select-profile"]
    assert slugs(need_google=True) == ["fixture-select-legacy", "fixture-select-profile"]  # no 'osm:' placeholder
    assert slugs(has_profile="google") == ["fixture-select-profile"]
    assert slugs(no_profile="google") == ["fixture-select-legacy", "fixture-select-placeholder"]
    with pytest.raises(SystemExit, match="at most"):
        reprocare_bot.select_facilities(db, None, True, reprocare_bot.MAX_FACILITIES_PER_RUN + 1)
    with pytest.raises(SystemExit):
        reprocare_bot.main(["facebook", "--all", "--limit", str(reprocare_bot.MAX_FACILITIES_PER_RUN + 1)])


def test_discovery_does_not_duplicate_an_existing_facility_without_a_place_id(db, capsys):
    """Regression: Google discovery created a second record for an OpenStreetMap facility that had no Google place id.
    A same-name facility within 300 m is reported for review instead; nothing is merged or linked automatically.
    Branches (same name far away) and different names next door are still separate facilities."""
    import reprocare_bot
    from facilities import upsert_from_place
    from app.models import Facility, FacilityExternalProfile

    osm = Facility(slug="fixture-langata-osm", name="Fixture Langata Hospital", facility_type="hospital", town="Nairobi",
                   county="Nairobi", is_demo=False, latitude=-1.3400, longitude=36.7600, external_id="osm:node/9000000010")
    db.add(osm)
    db.commit()
    place = {**PLACE, "id": "ChIJfixtureLangataPlace1", "displayName": {"text": "Fixture Langata Hospital Ltd"},
             "location": {"latitude": -1.3405, "longitude": 36.7604}, "reviews": []}
    facility, outcome = upsert_from_place(db, place)
    assert facility is None and outcome == "skipped:possible duplicate of fixture-langata-osm"
    assert db.query(Facility).filter(Facility.name.like("Fixture Langata Hospital%")).count() == 1
    assert db.query(FacilityExternalProfile).filter_by(external_id="ChIJfixtureLangataPlace1").count() == 0

    branch, outcome = upsert_from_place(db, {**place, "id": "ChIJfixtureLangataBranch", "location": {"latitude": -1.30, "longitude": 36.70}})
    assert outcome == "created" and branch.id != osm.id
    neighbour, outcome = upsert_from_place(db, {**place, "id": "ChIJfixtureLangataNeighb", "displayName": {"text": "Fixture Langata Dental Clinic"}})
    assert outcome == "created" and neighbour.id != osm.id
    db.rollback()

    # The reviewer links the place id explicitly: preview first, then --apply. No Google request is made.
    reprocare_bot.main(["link-google", "--facility", "fixture-langata-osm", "--place-id", "ChIJfixtureLangataPlace1"])
    assert "PREVIEW ONLY" in capsys.readouterr().out
    db.expire_all()
    assert db.query(FacilityExternalProfile).filter_by(facility_id=osm.id).count() == 0
    reprocare_bot.main(["link-google", "--facility", "fixture-langata-osm", "--place-id", "ChIJfixtureLangataPlace1", "--apply"])
    db.expire_all()
    profile = db.query(FacilityExternalProfile).filter_by(facility_id=osm.id, platform="google").one()
    assert profile.external_id == "ChIJfixtureLangataPlace1" and profile.match_method == "manual_review"
    facility, outcome = upsert_from_place(db, place)  # discovery now updates the linked facility instead
    db.commit()
    assert outcome == "updated" and facility.id == osm.id and facility.name == "Fixture Langata Hospital"
    with pytest.raises(SystemExit, match="already linked"):
        reprocare_bot.main(["link-google", "--facility", "fixture-select-profile", "--place-id", "ChIJfixtureLangataPlace1", "--apply"])
    with pytest.raises(SystemExit, match="place id"):
        reprocare_bot.main(["link-google", "--facility", "fixture-langata-osm", "--place-id", "not a place", "--apply"])
