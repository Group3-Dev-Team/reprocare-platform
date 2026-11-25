"""Find Care "Public reviews" filter (has_public_reviews). TEST FIXTURES only, in the disposable test database.

Counts a facility when public reviews are actually available for it, without asking any external service:
  * published, facility-level written comments (approved Facebook posts, visible TikTok comments), or
  * a stored Google Maps rating with at least one rating (written Google reviews load live on the page).
A linked profile alone, organisation-wide Facebook activity, unapproved or held comments do not count.
"""

from app.database.session import SessionLocal
from app.models import ExternalComment, ExternalPost, FacilityExternalProfile


def _post(db, facility, platform, n, *, visible=True, scope=None, comment_status="visible", text="Test fixture: helpful staff at the clinic."):
    post = ExternalPost(facility_id=facility.id, platform=platform, external_id=f"fixture-pr-{n}", url=f"https://www.tiktok.com/@fixture/video/{n}",
                        is_visible=visible, facebook_scope=scope)
    db.add(post)
    db.flush()
    db.add(ExternalComment(post_id=post.id, facility_id=facility.id, platform=platform, external_id=f"fixture-pr-c{n}",
                           author_name="Fixture Person", text=text, status=comment_status))


def test_public_reviews_filter(client, make_facility, monkeypatch):
    from app.services import google_places_service

    called = []
    monkeypatch.setattr(google_places_service, "written_reviews", lambda *a, **k: called.append(a))
    f = {key: make_facility(name=f"Prfixture {key}", county="Kisumu" if key != "tiktok_nairobi" else "Nairobi", is_demo=False,
                            latitude=-0.1, longitude=34.7)
         for key in ("tiktok", "tiktok_nairobi", "fb_facility", "fb_org", "fb_unapproved", "held_only", "google_rated",
                     "google_unrated", "profile_only", "nothing")}
    with SessionLocal() as db:
        _post(db, f["tiktok"], "tiktok", 1)
        _post(db, f["tiktok_nairobi"], "tiktok", 2)
        _post(db, f["fb_facility"], "facebook", 3, scope="facility")
        _post(db, f["fb_org"], "facebook", 4, scope="organization")
        _post(db, f["fb_unapproved"], "facebook", 5, scope=None, comment_status="held")
        _post(db, f["held_only"], "tiktok", 6, comment_status="held")
        db.add(FacilityExternalProfile(facility_id=f["google_rated"].id, platform="google", external_id="ChIJfixturePrRated001", rating=4.3, rating_count=17))
        db.add(FacilityExternalProfile(facility_id=f["google_unrated"].id, platform="google", external_id="ChIJfixturePrUnrated01", rating=None, rating_count=None))
        db.add(FacilityExternalProfile(facility_id=f["profile_only"].id, platform="facebook", external_id="fixturepage", url="https://www.facebook.com/fixturepage"))
        db.commit()

    def names(**params):
        body = client.get("/api/facilities", params={"q": "Prfixture", "page_size": 40, "sort": "name", **params}).json()
        return [item["name"].removeprefix("Prfixture ") for item in body["items"]], body["total"]

    assert names(has_public_reviews=True) == (["fb_facility", "google_rated", "tiktok", "tiktok_nairobi"], 4)
    assert names(has_public_reviews=False)[1] == 10
    assert names(has_public_reviews=True, county="Kisumu") == (["fb_facility", "google_rated", "tiktok"], 3)
    assert names(has_public_reviews=True, page_size=2, page=2) == (["tiktok", "tiktok_nairobi"], 4)
    markers = client.get("/api/facilities/markers", params={"q": "Prfixture", "has_public_reviews": True}).json()
    assert len(markers) == 4
    assert called == []  # computing the filter never calls Google
