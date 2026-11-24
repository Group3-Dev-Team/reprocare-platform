"""Local collected feedback uses consent-independent reads over disposable fixtures."""

from fastapi.testclient import TestClient

from app.config import settings
from app.database.session import SessionLocal
from app.main import app
from app.models import ExternalPost, Facility
from app.services.external_feedback_service import upsert_profile
# Reuse the data-bot module's branch-local fixtures (named facilities, factory-made admin) so this runs on main alone.
from tests.test_external_feedback import KEY, _named_facilities, admin_headers, fb_batch  # noqa: F401


BASE = "/api/local-collection/facebook"


def test_local_collection_requires_development_and_loopback(client, monkeypatch):
    route = f"{BASE}/facilities/mwangaza/posts"
    local = TestClient(app, base_url="http://localhost", client=("127.0.0.1", 12345))
    monkeypatch.setattr(settings, "environment", "production")
    assert local.get(route).status_code == 404
    monkeypatch.setattr(settings, "environment", "development")
    assert client.get(route).status_code == 404
    assert local.get(route, headers={"Origin": "https://outside.example"}).status_code == 404
    assert local.get(route, headers={"X-Forwarded-For": "203.0.113.1"}).status_code == 404
    assert local.get(route, headers={"X-Forwarded-Host": "outside.example"}).status_code == 404
    assert local.get(route, headers={"Forwarded": "for=203.0.113.1"}).status_code == 404
    assert local.get(route, headers={"Host": "outside.example"}).status_code == 404
    assert local.get(route).headers["Cache-Control"] == "no-store"


def test_collected_facebook_screening_attribution_and_moderation(client, admin_headers, monkeypatch):
    branch = "collected-fixture-hospital"
    first = "aar-healthcare-collected-fixture-one"
    second = "aar-healthcare-collected-fixture-two"
    mismatch = "unrelated-collected-fixture"
    host = "https://www.facebook.com/"
    branch_page = "collectedfixturehospital"
    shared_page = "aarhealthcareofficial"
    sources = [
        (branch, "Collected Fixture Hospital", branch_page),
        (first, "AAR Healthcare Collected Fixture One", shared_page),
        (second, "AAR Healthcare Collected Fixture Two", shared_page),
        (mismatch, "Unrelated Collected Fixture", shared_page),
        ("wix", "Wix", "wix"),
    ]
    with SessionLocal() as db:
        for slug, name, page in sources:
            facility = Facility(slug=slug, name=name, facility_type="clinic", town="Nairobi",
                                county="Nairobi", website="https://facility.example", is_demo=False)
            db.add(facility)
            db.flush()
            upsert_profile(db, facility, "facebook", page, url=host + page, match_method="official_website")
        db.commit()

    def batch(slug, page, identifier, comments=None):
        return fb_batch(slug=slug, ext=identifier, post_url=f"{host}{page}/posts/{identifier}",
                        comments=comments if comments is not None else [
                            {"external_id": f"{identifier}-comment", "text": "What are your clinic hours?"},
                        ])

    legacy = "fixture-collected-legacy"
    unreviewed = "fixture-collected-new"
    comments = [
        {"external_id": f"{unreviewed}-root", "text": "How much does it cost?"},
        {"external_id": f"{unreviewed}-reply", "parent_external_id": f"{unreviewed}-root",
         "text": "The clinic takes appointments."},
        {"external_id": f"{unreviewed}-second", "text": "The clinic staff were helpful."},
        {"external_id": f"{unreviewed}-irrelevant", "text": "Great speech from the political rally."},
        {"external_id": f"{unreviewed}-private", "text": "My test results. Contact me at patient@example.org."},
        {"external_id": f"{unreviewed}-hidden", "text": "Hidden clinic comment."},
        {"external_id": f"{unreviewed}-unsafe-reply", "parent_external_id": f"{unreviewed}-private",
         "text": "Talk to a doctor at the clinic."},
    ]
    batches = [
        batch(branch, branch_page, legacy), batch(branch, branch_page, unreviewed, comments),
        batch(branch, "wrongpage", "fixture-collected-wrong-page"),
        batch(first, shared_page, "fixture-collected-shared"),
        batch(second, shared_page, "fixture-collected-shared-next"),
        batch(mismatch, shared_page, "fixture-collected-other-group"),
        batch("wix", "wix", "fixture-collected-generic"),
    ]
    imported = client.post("/api/import/external-feedback", json={"batches": batches}, headers=KEY).json()
    assert imported["imported"] == 7 and imported["comments_created"] == 13
    from app.models import ExternalComment

    with SessionLocal() as db:
        old = db.query(ExternalPost).filter_by(external_id=legacy).one()
        old.is_visible = True
        db.query(ExternalComment).filter_by(external_id=f"{unreviewed}-hidden").one().status = "hidden"
        post_id = db.query(ExternalPost).filter_by(external_id=unreviewed).one().id
        db.commit()

    monkeypatch.setattr(settings, "environment", "development")
    local = TestClient(app, base_url="http://localhost", client=("127.0.0.1", 12345))
    listing = f"{BASE}/facilities/{branch}/posts"
    page_1 = local.get(listing, params={"page_size": 1}).json()
    page_2 = local.get(listing, params={"page_size": 1, "page": 2}).json()
    assert (page_1["total"], page_1["pages"], page_1["comment_total"]) == (2, 2, 4)
    assert page_2["comment_total"] == 4
    assert page_1["items"][0]["id"] != page_2["items"][0]["id"]
    assert all(row["display_status"] == "collected" and row["attribution_scope"] == "facility"
               for row in page_1["items"] + page_2["items"])
    assert not page_1["related_organizations"]
    public = f"/api/facilities/{branch}/public-feedback/posts"
    assert client.get(public).json()["total"] == 0
    thread_url = f"{BASE}/posts/{post_id}/comments"
    thread = local.get(thread_url, params={"page_size": 1}).json()
    next_thread = local.get(thread_url, params={"page_size": 1, "page": 2}).json()
    assert (thread["total"], thread["pages"], thread["post"]["comment_count"]) == (2, 2, 3)
    assert thread["items"][0]["text"] == "How much does it cost?"
    assert thread["items"][0]["replies"][0]["text"] == "The clinic takes appointments."
    assert next_thread["items"][0]["text"] == "The clinic staff were helpful."
    assert not next_thread["items"][0]["replies"] and next_thread["post"]["comment_count"] == 3
    assert thread["post"]["url"] == batches[1]["post"]["url"]
    assert client.get(f"/api/external-posts/{post_id}/comments").status_code == 404

    for slug in (first, second):
        route = f"{BASE}/facilities/{slug}/posts"
        [summary] = local.get(route).json()["related_organizations"]
        assert summary["key"] == shared_page and summary["name"] == "AAR Healthcare"
        params = {"scope": "organization", "organization": shared_page, "page_size": 1}
        urls = set()
        for page in (1, 2):
            org = local.get(route, params={**params, "page": page}).json()
            assert (org["total"], org["pages"], org["comment_total"]) == (2, 2, 2)
            assert all(org[key] == summary[key] for key in ("total", "comment_total", "written_total"))
            assert org["items"][0]["attribution_scope"] == "organization"
            urls.add(org["items"][0]["url"])
        assert urls == {item["post"]["url"] for item in batches[3:5]}
    assert local.get(f"{BASE}/facilities/{mismatch}/posts", params={"scope": "organization"}).json()["total"] == 0
    assert local.get(f"{BASE}/facilities/wix/posts").json()["total"] == 0

    action = f"/api/admin/facebook-feedback/{post_id}/moderate"
    reviewed_at = client.post(action, headers=admin_headers, json={
        "decision": "publish", "scope": "facility", "note": "Reviewed test fixture.",
        "reviewed_at": None, "comment_ids": [thread["items"][0]["id"]],
    }).json()["reviewed_at"]
    assert client.get(public).json()["total"] == 1
    assert local.get(listing).json()["total"] == 1
    assert local.get(f"{BASE}/posts/{post_id}/comments").status_code == 404
    assert client.post(action, headers=admin_headers, json={
        "decision": "withhold", "note": "Withheld test fixture.", "reviewed_at": reviewed_at,
    }).status_code == 200
    assert client.get(public).json()["total"] == 0
    assert local.get(listing).json()["total"] == 1
    assert local.get(f"{BASE}/posts/{post_id}/comments").status_code == 404
