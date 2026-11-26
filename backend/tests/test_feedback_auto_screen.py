"""Automatic screening of public comments and the Public reviews filter. All records are TEST FIXTURES."""

import pytest

from app.config import settings
from app.database.session import SessionLocal
from app.models import ExternalComment, ExternalPost, Facility, FacilityExternalProfile
from app.services.external_feedback_service import mask_contact_details
from app.services.feedback_auto_screen import EXCLUDE, PUBLISH, REVIEW, classify, is_facility_author, mask_contacts

KEY = {"X-Import-Key": "test-import-key"}
PAGE = "autoscreenfixturepage"


@pytest.mark.parametrize("text, action, reason", [
    ("The nurses in maternity were kind and professional", PUBLISH, "care_experience_or_service_comment"),
    ("How much is the consultation fee?", PUBLISH, "service_question"),
    ("Do you treat fibroids?", PUBLISH, "service_question"),
    ("Can SHA be used?", PUBLISH, "service_question"),
    ("Mnafanyanga colonoscopy?", PUBLISH, "service_question"),
    ("Money making is more important here than helping the client!!!", PUBLISH, "care_experience_or_service_comment"),
    ("Congratulations", EXCLUDE, "greeting_or_prayer_only"),
    ("Amen", EXCLUDE, "greeting_or_prayer_only"),
    ("N Njoki", EXCLUDE, "too_short_or_tag_only"),
    ("Any vacancy for clinical officer", EXCLUDE, "job_request"),
    ("Kindly need a job at this hospital, I am a professional", EXCLUDE, "job_request"),
    ("0712345678", EXCLUDE, "contact_details_only"),
    ("#YourHealthOurPriority", EXCLUDE, "hashtags_or_mentions_only"),
    ("Keeping the domain and SSL in one place helps small businesses", EXCLUDE, "advertising_or_off_topic_promotion"),
    ("I was pregnant and the doctor ignored me", REVIEW, "personal_health_detail"),
    ("My HIV test results were shared", REVIEW, "personal_health_detail"),
    ("My mother died because of negligence at the clinic", REVIEW, "serious_allegation"),
    ("Do you accept CIC insurance from National Police service", PUBLISH, "service_question"),
])
def test_classify(text, action, reason):
    decision = classify(text, "Fixture Hospital")
    assert (decision.action, decision.reason) == (action, reason)


def test_facility_comments_and_author_matching():
    reply = classify("Yes we do", by_facility=True, is_reply=True)
    assert (reply.action, reply.reason) == (PUBLISH, "facility_reply")
    assert classify("Join our team today", by_facility=True).action == EXCLUDE
    assert is_facility_author("Marie Stopes Kenya", "Marie Stopes Kenyatta Market", "marie.stopes.kenya.1985")
    assert not is_facility_author("Karen Wanjiru", "The Karen Hospital", "tkh2006")
    assert not is_facility_author("Jane Doe", "Fixture Hospital", PAGE)


def test_contact_masking_keeps_prices():
    assert mask_contacts("call 723 707 797 or 0712345678, a@b.co") == "call [phone number removed] or [phone number removed], [email removed]"
    assert mask_contacts("an ultrasound costs KES 2,500-3,000") == "an ultrasound costs KES 2,500-3,000"
    assert "723" not in mask_contact_details("Please call 723 707 797")


@pytest.fixture
def linked_facility(make_facility):
    slug = "auto-screen-fixture"
    with SessionLocal() as db:
        if db.query(Facility).filter_by(slug=slug).first() is None:
            make_facility(slug=slug, name="Auto Screen Fixture Hospital")
    with SessionLocal() as db:
        facility = db.query(Facility).filter_by(slug=slug).one()
        if not db.query(FacilityExternalProfile).filter_by(facility_id=facility.id, platform="facebook").first():
            db.add(FacilityExternalProfile(facility_id=facility.id, platform="facebook", external_id=PAGE,
                                           url=f"https://www.facebook.com/{PAGE}", display_name="", match_method="facility_page",
                                           photos=[], details={}))
            db.commit()
    return slug


def _batch(slug, ext, page=PAGE):
    return {"platform": "facebook", "facility_slug": slug, "post": {
        "external_id": ext, "url": f"https://www.facebook.com/{page}/posts/pfbid{ext}", "author_name": "", "caption": "Clinic days",
        "match_method": "facility_page_post"}, "comments": [
        {"external_id": f"{ext}-1", "author_name": "Fixture Person", "text": "Good service at the antenatal clinic"},
        {"external_id": f"{ext}-2", "author_name": "Fixture Person Two", "text": "Congratulations"},
        {"external_id": f"{ext}-3", "author_name": "Fixture Person Three", "text": "I was pregnant and they turned me away"},
        {"external_id": f"{ext}-4", "parent_external_id": f"{ext}-1", "author_name": "Auto Screen Fixture Hospital",
         "text": "Thank you for visiting"},
    ]}


def _statuses(ext):
    with SessionLocal() as db:
        post = db.query(ExternalPost).filter_by(external_id=ext).one()
        comments = {c.external_id: c.status for c in db.query(ExternalComment).filter_by(post_id=post.id)}
        return post, comments


def test_facebook_import_waits_for_moderation_when_automatic_screening_is_off(client, linked_facility, monkeypatch):
    monkeypatch.setattr(settings, "facebook_auto_screening", False)
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [_batch(linked_facility, "autooff")]}).status_code == 200
    post, comments = _statuses("autooff")
    assert not post.is_visible and post.facebook_scope is None and set(comments.values()) == {"held"}


def test_facebook_import_screens_automatically(client, linked_facility, monkeypatch):
    monkeypatch.setattr(settings, "facebook_auto_screening", True)
    assert client.post("/api/import/external-feedback", headers=KEY, json={"batches": [_batch(linked_facility, "autoon")]}).status_code == 200
    post, comments = _statuses("autoon")
    assert post.is_visible and post.facebook_scope == "facility" and post.facebook_review_note == "Automatic screening"
    assert comments == {"autoon-1": "visible", "autoon-2": "hidden", "autoon-3": "held", "autoon-4": "visible"}
    shown = client.get(f"/api/external-posts/{post.id}/comments").json()["items"]
    assert [c["text"] for c in shown] == ["Good service at the antenatal clinic"] and len(shown[0]["replies"]) == 1
    assert client.get("/api/facilities?has_public_reviews=true&q=Auto Screen Fixture").json()["total"] == 1


def test_automatic_screening_needs_the_facilitys_own_page(client, linked_facility, monkeypatch):
    monkeypatch.setattr(settings, "facebook_auto_screening", True)
    client.post("/api/import/external-feedback", headers=KEY, json={"batches": [_batch(linked_facility, "otherpage", page="someotherpage")]})
    post, comments = _statuses("otherpage")
    assert not post.is_visible and set(comments.values()) == {"held"}


def test_public_reviews_ignores_a_linked_google_place_without_feedback_or_rating(client, make_facility):
    make_facility(slug="google-linked-fixture", name="Google Linked Fixture Clinic")
    assert client.get("/api/facilities?has_public_reviews=true&q=Google Linked Fixture").json()["total"] == 0
    with SessionLocal() as db:
        facility = db.query(Facility).filter_by(slug="google-linked-fixture").one()
        db.add(FacilityExternalProfile(facility_id=facility.id, platform="google", external_id="ChIJfixtureLinkedPlace01",
                                       url="", display_name="", match_method="fixture", photos=[], details={}))
        db.commit()
    assert client.get("/api/facilities?has_public_reviews=true&q=Google Linked Fixture").json()["total"] == 0
