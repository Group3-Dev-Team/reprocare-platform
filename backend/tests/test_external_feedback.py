"""External public feedback (SYSTEM 2): import rules, pagination, display, and — most
importantly — that it never changes the ReproCare rating (SYSTEM 1).

All records below are TEST FIXTURES written into the isolated reprocare_test database. The URLs use
real platform hostnames only because the importer rejects anything else; they point at nothing.
"""

import pytest

from app.services.external_feedback_service import display_author


# --- Branch-local fixtures -------------------------------------------------------------------------------
# These tests belong to the data-bot workstream and run on the shared foundation alone. They create the few
# facilities they name and their own users. Checks that need another workstream's endpoints (discovery
# search, facility detail, county list, admin import history) are skipped until those routers are registered.
from app.database.session import SessionLocal as _SessionLocal  # noqa: E402
from app.main import app as _app  # noqa: E402
from app.models import Facility as _Facility  # noqa: E402

_FACILITIES = {
    "mwangaza": {"name": "Mwangaza Health Centre", "town": "Nakuru", "county": "Nakuru", "facility_type": "health_centre"},
    "kipepeo": {"name": "Kipepeo Women's Hospital", "town": "Nairobi", "county": "Nairobi", "facility_type": "hospital"},
    "tumaini": {"name": "Tumaini Diagnostic Laboratory", "town": "Kisumu", "county": "Kisumu", "facility_type": "laboratory"},
}


def _has_route(path):
    return any(getattr(r, "path", None) == path for r in _app.routes)


needs_route = lambda path: pytest.mark.skipif(not _has_route(path), reason=f"needs {path} from another workstream (integration test)")  # noqa: E731


@pytest.fixture(autouse=True)
def _named_facilities(make_facility):
    with _SessionLocal() as db:
        existing = {slug for (slug,) in db.query(_Facility.slug).filter(_Facility.slug.in_(_FACILITIES))}
    for slug, fields in _FACILITIES.items():
        if slug not in existing:
            make_facility(slug=slug, **fields)


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


@pytest.fixture()
def new_patient(make_user):
    user, headers = make_user()
    return headers, {"id": user.id, "email": user.email}

KEY = {"X-Import-Key": "test-import-key"}
FB_POST = "https://web.facebook.com/testfixturepage/posts/pfbidTESTFIXTURE0001"


def fb_batch(slug="mwangaza", post_url=FB_POST, ext="fixture-fb-post-1", comments=None):
    return {
        "platform": "facebook",
        "facility_slug": slug,
        "post": {"external_id": ext, "url": post_url, "author_name": "Test Fixture Page", "caption": "Test fixture post about antenatal clinic days.", "match_method": "facility_page_post"},
        "comments": comments
        if comments is not None
        else [
            {"external_id": f"{ext}-c1", "author_name": "Fixture Person One", "text": "Test fixture: the nurses at the clinic were kind.", "like_count": 4},
            {"external_id": f"{ext}-c2", "author_name": "Fixture Person Two", "text": "Test fixture: call me on 0712345678 about the clinic."},
            {"external_id": f"{ext}-c3", "parent_external_id": f"{ext}-c1", "author_name": "Test Fixture Page", "author_is_facility": True, "text": "Test fixture reply from the facility."},
            {"external_id": f"{ext}-c4", "author_name": "Fixture Person Three", "text": "   "},
        ],
    }


def test_import_requires_key_or_admin(client, new_patient):
    body = {"batches": [fb_batch()]}
    assert client.post("/api/import/external-feedback", json=body).status_code == 401
    assert client.post("/api/import/external-feedback", json=body, headers={"X-Import-Key": "wrong"}).status_code == 401
    patient, _ = new_patient
    assert client.post("/api/import/external-feedback", json=body, headers=patient).status_code == 401


def approve_fixture(client, admin_headers, source_url, scope="facility"):
    queue = client.get("/api/admin/facebook-feedback", headers=admin_headers).json()
    post = next(p for p in queue["items"] if p["source_url"] == source_url)
    detail = client.get(f"/api/admin/facebook-feedback/{post['id']}", headers=admin_headers).json()
    result = client.post(
        f"/api/admin/facebook-feedback/{post['id']}/moderate", headers=admin_headers,
        json={"decision": "publish", "scope": scope, "note": "Reviewed fixture evidence.",
              "comment_ids": [c["id"] for c in detail["comments"]], "reviewed_at": detail["reviewed_at"]},
    )
    assert result.status_code == 200, result.text
    return post["id"]


def test_import_screening_threads_and_idempotency(client, admin_headers):
    r = client.post("/api/import/external-feedback", json={"batches": [fb_batch()]}, headers=KEY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 1 and body["errors"] == []
    assert body["comments_created"] == 3  # the blank comment is never stored

    again = client.post("/api/import/external-feedback", json={"batches": [fb_batch()]}, headers=KEY).json()
    assert again["comments_created"] == 0 and again["comments_skipped"] == 3

    posts_url = "/api/facilities/mwangaza/public-feedback/posts"
    assert client.get(posts_url, params={"platform": "facebook"}).json()["total"] == 0
    approve_fixture(client, admin_headers, FB_POST, "organization")
    posts = client.get(posts_url, params={"platform": "facebook"}).json()
    post = next(p for p in posts["items"] if p["url"] == FB_POST)
    assert post["comment_count"] == 3
    assert post["attribution_scope"] == "organization"
    if _has_route("/api/facilities"):  # discovery filter (integration)
        assert client.get("/api/facilities", params={"has_public_feedback": True, "q": "Mwangaza"}).json()["total"] == 0
    assert post["caption"].startswith("Test fixture post")
    comments = client.get(f"/api/external-posts/{post['id']}/comments").json()
    assert comments["total"] == 2  # two top-level comments; the reply is nested under its parent
    top = next(c for c in comments["items"] if c["replies"])
    assert top["author"] == "Fixture O."  # people are shown as first name + initial
    assert top["platform_label"] == "Facebook"
    assert top["replies"][0]["author_is_facility"] is True and top["replies"][0]["author"] == "Test Fixture Page"
    phone = next(c for c in comments["items"] if "call me" in c["text"])
    assert "0712345678" not in phone["text"] and "[phone number hidden]" in phone["text"]  # masked on display

    from app.database.session import SessionLocal
    from app.models import ExternalComment

    with SessionLocal() as db:  # stored exactly as collected
        assert db.query(ExternalComment).filter_by(external_id="fixture-fb-post-1-c2").one().text.endswith("0712345678 about the clinic.")


def test_rejects_unknown_facility_bad_url_and_reattribution(client):
    bad = client.post(
        "/api/import/external-feedback",
        headers=KEY,
        json={
            "batches": [
                fb_batch(slug="no-such-facility", ext="fixture-x1"),
                fb_batch(post_url="https://evil.example.com/posts/1", ext="fixture-x2"),
                fb_batch(slug="kipepeo"),  # same post id as an earlier import, different facility
                {"platform": "facebook", "post": {"external_id": "fixture-x3", "url": FB_POST}, "comments": []},
            ]
        },
    ).json()
    assert bad["imported"] == 0 and len(bad["errors"]) == 4
    assert "different facility" in bad["errors"][2]["error"]


@needs_route("/api/facilities/{slug}")
def test_google_rating_never_changes_reprocare_rating(client):
    before = client.get("/api/facilities/mwangaza").json()["rating"]
    listing = client.get("/api/facilities", params={"sort": "rating", "q": "Mwangaza"}).json()["items"][0]["rating"]
    from app.database.session import SessionLocal
    from app.models import Facility
    from app.services.external_feedback_service import upsert_profile

    with SessionLocal() as db:
        facility = db.query(Facility).filter_by(slug="mwangaza").one()
        upsert_profile(db, facility, "google", "fixture-place-id-1", url="https://www.google.com/maps/place/?q=place_id:fixture-place-id-1", rating=1.2, rating_count=999, match_method="google_place_id")
        db.commit()

    r = client.post(
        "/api/import/external-feedback",
        headers=KEY,
        json={
            "batches": [
                {
                    "platform": "google",
                    "google_place_id": "fixture-place-id-1",
                    "post": {"external_id": "fixture-place-id-1", "url": "https://www.google.com/maps/place/?q=place_id:fixture-place-id-1", "match_method": "google_place_id"},
                    "comments": [{"external_id": f"fixture-g{i}", "author_name": "Fixture Reviewer", "text": f"Test fixture Google review {i}", "source_rating": 1} for i in range(5)],
                }
            ]
        },
    ).json()
    assert r["comments_created"] == 5

    card = client.get("/api/facilities", params={"q": "Mwangaza"}).json()["items"][0]
    assert card["google_rating"]["rating"] == 1.2
    assert card["google_rating"]["rating_count"] == 999

    after = client.get("/api/facilities/mwangaza").json()["rating"]
    assert after == before  # ReproCare rating comes only from ReproCare reviews
    assert client.get("/api/facilities", params={"sort": "rating", "q": "Mwangaza"}).json()["items"][0]["rating"] == listing
    reviews = client.get("/api/facilities/mwangaza/reviews").json()
    assert all(item["source"] == "ReproCare" for item in reviews["items"])

    summary = client.get("/api/facilities/mwangaza/public-feedback").json()
    assert summary["google"]["rating"] == 1.2 and summary["google"]["rating_count"] == 999
    assert "Not a ReproCare rating" in summary["google"]["attribution"]
    google = next(p for p in summary["platforms"] if p["platform"] == "google")
    assert google["comments"] == 5


def test_post_pagination(client, admin_headers):
    batches = [
        fb_batch(slug="tumaini", ext=f"fixture-page-{i}", post_url=f"https://web.facebook.com/testfixturepage/posts/pfbidPAGE{i}",
                 comments=[{"external_id": f"fixture-page-{i}-c{j}", "author_name": "Fixture", "text": f"Test fixture comment {j}"} for j in range(12)])
        for i in range(7)
    ]
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": batches}).json()["imported"] == 7
    for batch in batches:
        approve_fixture(client, admin_headers, batch["post"]["url"])
    first = client.get("/api/facilities/tumaini/public-feedback/posts", params={"page_size": 3}).json()
    assert first["total"] == 7 and first["pages"] == 3 and len(first["items"]) == 3
    if _has_route("/api/facilities"):  # discovery filter (integration)
        assert client.get("/api/facilities", params={"has_public_feedback": True, "q": "Tumaini"}).json()["total"] >= 1
    assert len(first["items"][0]["preview"]) == 3
    last = client.get("/api/facilities/tumaini/public-feedback/posts", params={"page_size": 3, "page": 3}).json()
    assert len(last["items"]) == 1
    pid = first["items"][0]["id"]
    c1 = client.get(f"/api/external-posts/{pid}/comments", params={"page_size": 5}).json()
    c3 = client.get(f"/api/external-posts/{pid}/comments", params={"page_size": 5, "page": 3}).json()
    assert c1["total"] == 12 and c1["pages"] == 3 and len(c3["items"]) == 2
    assert {c["id"] for c in c1["items"]}.isdisjoint({c["id"] for c in c3["items"]})
    assert client.get("/api/facilities/tumaini/public-feedback/posts", params={"page_size": 99}).status_code == 422


def test_facebook_moderation_access_and_visibility(client, admin_headers, new_patient):
    from app.database.session import SessionLocal
    from app.models import ExternalPost

    patient, _ = new_patient
    queue = "/api/admin/facebook-feedback"
    assert client.get(queue).status_code == 401
    assert client.get(queue, headers=patient).status_code == 403
    url = "https://web.facebook.com/testfixturepage/posts/pfbidMODERATION"
    batch = fb_batch(slug="kipepeo", ext="fixture-moderation", post_url=url)
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [batch]}).json()["imported"] == 1
    with SessionLocal() as db:
        legacy = db.query(ExternalPost).filter_by(external_id="fixture-moderation").one()
        legacy.is_visible = True
        db.commit()
        post_id = legacy.id
    detail = f"{queue}/{post_id}"
    action = f"{detail}/moderate"
    thread = f"/api/external-posts/{post_id}/comments"
    assert client.get(thread).status_code == 404
    record = client.get(detail, headers=admin_headers).json()
    assert record["previously_visible"] is True
    parent, other, reply = record["comments"]
    payload = {"decision": "publish", "scope": "facility", "note": "Fixture branch confirmed.",
               "comment_ids": [reply["id"]], "reviewed_at": None}
    assert client.post(action, headers=patient, json=payload).status_code == 403
    assert client.post(action, headers=admin_headers, json=payload).status_code == 422
    payload["comment_ids"] = [parent["id"], reply["id"]]
    published = client.post(action, headers=admin_headers, json=payload)
    assert published.status_code == 200, published.text
    assert published.json()["published"] is True
    full_thread = client.get(thread).json()
    assert full_thread["post"]["comment_count"] == 2
    assert full_thread["items"][0]["replies"][0]["id"] == reply["id"]
    assert all(c["id"] != other["id"] for c in full_thread["items"])

    batch["comments"] = [{"external_id": "fixture-moderation-new", "text": "Fixture newly imported comment"}]
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [batch]}).json()["comments_created"] == 1
    assert client.get(thread).json()["post"]["comment_count"] == 2
    assert client.post(action, headers=admin_headers, json=payload).status_code == 409
    withheld = client.post(action, headers=admin_headers, json={
        "decision": "withhold", "note": "Fixture review withdrawn.", "reviewed_at": published.json()["reviewed_at"],
    })
    assert withheld.status_code == 200
    assert client.get(thread).status_code == 404
    assert len(client.get(detail, headers=admin_headers).json()["comments"]) == 4


def test_hidden_status_respected_if_set_in_database(client):
    """Rows can still be taken down directly in the database (status = 'hidden'); the API then omits them."""
    from app.database.session import SessionLocal
    from app.models import ExternalComment

    post = next(p for p in client.get("/api/facilities/mwangaza/public-feedback/posts", params={"platform": "facebook"}).json()["items"] if p["url"] == FB_POST)
    with SessionLocal() as db:
        row = db.query(ExternalComment).filter_by(external_id="fixture-fb-post-1-c2").one()
        row.status = "hidden"
        db.commit()
    texts = [c["text"] for c in client.get(f"/api/external-posts/{post['id']}/comments").json()["items"]]
    assert not any("call me" in t for t in texts)
    with SessionLocal() as db:
        db.query(ExternalComment).filter_by(external_id="fixture-fb-post-1-c2").one().status = "visible"
        db.commit()


def test_public_feedback_empty_and_missing(client):
    empty = client.get("/api/facilities/kipepeo/public-feedback").json()
    assert empty["total_comments"] == 0 and empty["google"] is None
    assert client.get("/api/facilities/kipepeo/public-feedback/posts").json()["total"] == 0
    assert client.get("/api/facilities/nope/public-feedback").status_code == 404
    assert client.get("/api/external-posts/999999/comments").status_code == 404


def test_hidden_parent_excludes_reply_from_public_counts(client, admin_headers):
    from app.database.session import SessionLocal
    from app.models import ExternalComment

    ext = "fixture-hidden-parent"
    batch = fb_batch(
        slug="kipepeo",
        ext=ext,
        post_url="https://web.facebook.com/testfixturepage/posts/pfbidHIDDENPARENT",
        comments=[
            {"external_id": f"{ext}-root", "text": "Fixture parent"},
            {"external_id": f"{ext}-reply", "parent_external_id": f"{ext}-root", "text": "Fixture reply"},
            {"external_id": f"{ext}-other", "text": "Fixture visible comment"},
        ],
    )
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [batch]}).json()["imported"] == 1
    approve_fixture(client, admin_headers, batch["post"]["url"])
    url = "/api/facilities/kipepeo/public-feedback"
    post = client.get(f"{url}/posts").json()["items"][0]
    assert post["comment_count"] == 3

    with SessionLocal() as db:
        db.query(ExternalComment).filter_by(external_id=f"{ext}-root").one().status = "hidden"
        db.commit()

    assert client.get(url).json()["total_comments"] == 1
    assert client.get(f"{url}/posts").json()["items"][0]["comment_count"] == 1
    thread = client.get(f"/api/external-posts/{post['id']}/comments").json()
    assert thread["post"]["comment_count"] == 1
    assert [item["text"] for item in thread["items"]] == ["Fixture visible comment"]

    with SessionLocal() as db:
        db.query(ExternalComment).filter_by(external_id=f"{ext}-other").one().status = "held"
        db.commit()

    assert client.get(url).json()["total_comments"] == 0
    assert client.get(f"{url}/posts").json()["total"] == 0


@needs_route("/api/counties")
def test_counties_endpoint(client):
    counties = client.get("/api/counties").json()
    assert len(counties) == 47
    nairobi = next(c for c in counties if c["county"] == "Nairobi")
    assert nairobi["facility_count"] >= 1


@pytest.mark.parametrize(
    "name,is_facility,expected",
    [("Robinson Kamau Otieno", False, "Robinson O."), ("solo_handle", False, "solo_handle"), ("", False, "Public user"), ("Aga Khan University Hospital", True, "Aga Khan University Hospital")],
)
def test_display_author(name, is_facility, expected):
    assert display_author(name, is_facility) == expected


def test_local_facebook_demo_leaves_public_moderation_intact(client, monkeypatch):
    from fastapi.testclient import TestClient
    from app.config import settings
    from app.database.session import SessionLocal
    from app.main import app
    from app.models import ExternalPost, Facility
    from app.routes import facebook_demo_routes
    from app.services.external_feedback_service import upsert_profile

    local = TestClient(app, base_url="http://localhost", client=("127.0.0.1", 12345))
    endpoint = "/api/local-demo/facebook"
    monkeypatch.setattr(settings, "environment", "development")
    assert local.get(f"{endpoint}/counts").status_code == 404
    monkeypatch.setattr(settings, "local_facebook_demo", True)
    assert client.get(f"{endpoint}/counts").status_code == 404
    assert local.get(f"{endpoint}/counts", headers={"Origin": "https://outside.example"}).status_code == 404
    monkeypatch.setattr(settings, "environment", "production")
    assert local.get(f"{endpoint}/counts").status_code == 404
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setitem(facebook_demo_routes.FACILITY_PAGES, "mwangaza", "localfixture")

    source = "https://www.facebook.com/localfixture/posts/demo123"
    batch = fb_batch(ext="fixture-local-demo", post_url=source)
    blocked = fb_batch(ext="fixture-demo-wix", post_url="https://www.facebook.com/wix/posts/demo456")
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [batch, blocked]}).json()["imported"] == 2
    with SessionLocal() as db:
        facility = db.query(Facility).filter_by(slug="mwangaza").one()
        upsert_profile(db, facility, "facebook", "localfixture", url="https://www.facebook.com/localfixture")
        wix_id = db.query(ExternalPost).filter_by(external_id="fixture-demo-wix").one().id
        db.commit()

    result = local.get(f"{endpoint}/posts", params={"scope": "facility", "slug": "mwangaza"})
    assert result.headers["Cache-Control"] == "no-store"
    post = result.json()["items"][0]
    assert post["url"] == source and post["comment_count"] == 3
    directory = local.get(f"{endpoint}/facilities").json()
    assert [(item["slug"], item["posts"]) for item in directory] == [("mwangaza", 1)]
    thread = local.get(f"{endpoint}/posts/{post['id']}/comments", params={"page_size": 1}).json()
    assert thread["total"] == 2 and len(thread["items"][0]["replies"]) == 1
    assert local.get(f"{endpoint}/posts/{wix_id}/comments").status_code == 404
    assert client.get(f"/api/external-posts/{post['id']}/comments").status_code == 404
    with SessionLocal() as db:
        assert db.get(ExternalPost, post["id"]).is_visible is False
