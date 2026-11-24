"""Health library articles: public reading (unchanged) and administrator writing (SCRUM-11)."""

import itertools
import json
from datetime import date
from pathlib import Path

import pytest

SEEDED = json.loads((Path(__file__).parents[1] / "app" / "database" / "reference_data.json").read_text())["articles"]
PUBLIC_LIST_KEYS = {"slug", "title", "category", "summary", "read_minutes", "related_services", "review_status", "updated_on"}
PUBLIC_DETAIL_KEYS = PUBLIC_LIST_KEYS | {"sections", "questions_to_ask", "references"}
ADMIN_DETAIL_KEYS = PUBLIC_DETAIL_KEYS | {"is_published"}
_unique = itertools.count(1)


@pytest.fixture()
def admin_headers(make_user):
    return make_user(role="admin")[1]


def _article(**fields):
    body = {
        "title": f"Understanding contraception choices aq{next(_unique)}x",
        "category": "Family planning",
        "summary": "An overview of common contraception methods and how to choose one.",
        "read_minutes": 5,
        "sections": [
            {"heading": "Your options", "paragraphs": ["There are several safe methods."], "list": ["Pills", "Implants"]},
            {"heading": "Talking to a provider", "paragraphs": ["A provider can help you decide."]},
        ],
        "questions_to_ask": ["Which method suits me?"],
        "references": [{"label": "Family planning handbook", "publisher": "World Health Organization"}],
        "related_services": ["contraception", "contraception", "gynae"],
    }
    body.update(fields)
    return body


def _create(client, headers, **fields):
    response = client.post("/api/admin/articles", headers=headers, json=_article(**fields))
    assert response.status_code == 201, response.text
    return response.json()


# --- Public reading is unchanged ----------------------------------------------------------------


def test_seeded_articles_are_public_with_unchanged_shapes(client):
    listed = client.get("/api/articles").json()
    assert {a["slug"] for a in SEEDED} <= {a["slug"] for a in listed}
    assert all(set(a) == PUBLIC_LIST_KEYS for a in listed)
    detail = client.get(f"/api/articles/{SEEDED[0]['slug']}").json()
    assert set(detail) == PUBLIC_DETAIL_KEYS
    assert detail["sections"] == SEEDED[0]["sections"]


# --- Creating -----------------------------------------------------------------------------------


def test_admin_creates_an_article(client, admin_headers):
    created = _create(client, admin_headers, title="  Antenatal visits explained  ")
    assert created["slug"] == "antenatal-visits-explained"
    assert created["title"] == "Antenatal visits explained"
    assert created["related_services"] == ["contraception", "gynae"]  # de-duplicated, order kept
    assert created["updated_on"] == date.today().isoformat()
    assert created["review_status"] == "Awaiting clinical review"
    # stored in the same JSON shape as the seeded articles
    assert created["sections"][0] == {"heading": "Your options", "paragraphs": ["There are several safe methods."], "list": ["Pills", "Implants"]}
    assert created["sections"][1] == {"heading": "Talking to a provider", "paragraphs": ["A provider can help you decide."]}
    assert set(created) == ADMIN_DETAIL_KEYS
    # a new article starts as an unpublished draft
    assert created["is_published"] is False
    assert client.get(f"/api/articles/{created['slug']}").status_code == 404

    published = client.post(f"/api/admin/articles/{created['slug']}/publish", headers=admin_headers).json()
    public = client.get(f"/api/articles/{created['slug']}").json()
    assert public == {k: v for k, v in published.items() if k != "is_published"}
    assert created["slug"] in {a["slug"] for a in client.get("/api/articles", params={"q": "antenatal visits"}).json()}


def test_same_title_gets_a_distinct_slug(client, admin_headers):
    first = _create(client, admin_headers, title="Preparing for a smear test")
    second = _create(client, admin_headers, title="Preparing for a smear test")
    assert second["slug"] == f"{first['slug']}-2"


def test_unknown_related_service_is_rejected(client, admin_headers):
    response = client.post("/api/admin/articles", headers=admin_headers, json=_article(related_services=["cervical", "astrology"]))
    assert response.status_code == 400
    assert "astrology" in response.json()["detail"]


@pytest.mark.parametrize(
    "change",
    [
        {"title": "abc"},
        {"title": "   ab   "},
        {"summary": "too short"},
        {"read_minutes": 0},
        {"sections": []},
        {"sections": [{"heading": "Empty section"}]},
        {"sections": [{"heading": "Blank line", "paragraphs": ["   "]}]},
        {"sections": [{"heading": "Extra key", "paragraphs": ["Text"], "image": "x.png"}]},
        {"sections": [{"paragraphs": ["No heading"]}]},
        {"questions_to_ask": ["?"]},
        {"references": [{"publisher": "No label"}]},
        {"author": "Someone"},
    ],
)
def test_invalid_article_content_is_rejected(client, admin_headers, change):
    assert client.post("/api/admin/articles", headers=admin_headers, json=_article(**change)).status_code == 422


# --- Editing ------------------------------------------------------------------------------------


def test_admin_edits_an_article(client, admin_headers):
    created = _create(client, admin_headers)
    new_sections = [{"heading": "Updated guidance", "list": ["Ask about side effects"]}]
    response = client.patch(
        f"/api/admin/articles/{created['slug']}",
        headers=admin_headers,
        json={"summary": "A refreshed overview of contraception methods.", "sections": new_sections, "related_services": ["contraception"]},
    )
    assert response.status_code == 200, response.text
    edited = response.json()
    assert edited["slug"] == created["slug"]  # links keep working
    assert edited["summary"] == "A refreshed overview of contraception methods."
    assert edited["sections"] == new_sections
    assert edited["related_services"] == ["contraception"]
    assert (edited["title"], edited["questions_to_ask"], edited["references"]) == (created["title"], created["questions_to_ask"], created["references"])
    assert edited["is_published"] is False  # editing does not publish
    assert client.get(f"/api/admin/articles/{created['slug']}", headers=admin_headers).json()["summary"] == edited["summary"]


def test_edit_validation(client, admin_headers):
    slug = _create(client, admin_headers)["slug"]
    url = f"/api/admin/articles/{slug}"
    assert client.patch(url, headers=admin_headers, json={"related_services": ["astrology"]}).status_code == 400
    assert client.patch(url, headers=admin_headers, json={"title": None}).status_code == 422
    assert client.patch(url, headers=admin_headers, json={"sections": []}).status_code == 422
    assert client.patch(url, headers=admin_headers, json={"slug": "new-slug"}).status_code == 422
    assert client.patch("/api/admin/articles/no-such-article", headers=admin_headers, json={"read_minutes": 3}).status_code == 404
    assert client.patch(url, headers=admin_headers, json={"is_published": True}).status_code == 422  # use /publish
    # an empty edit changes nothing
    assert client.patch(url, headers=admin_headers, json={}).json() == client.get(f"/api/admin/articles/{slug}", headers=admin_headers).json()


def test_seeded_articles_are_listed_for_administrators(client, admin_headers):
    listed = client.get("/api/admin/articles", headers=admin_headers).json()
    assert {a["slug"] for a in SEEDED} <= {a["slug"] for a in listed}
    detail = client.get(f"/api/admin/articles/{SEEDED[1]['slug']}", headers=admin_headers).json()
    assert detail["title"] == SEEDED[1]["title"]


# --- Permissions --------------------------------------------------------------------------------


def test_article_administration_is_admin_only(client, admin_headers, make_user, make_facility):
    slug = _create(client, admin_headers)["slug"]
    patient = make_user()[1]
    staff = make_user(role="facility_staff", facility=make_facility())[1]
    calls = [
        ("get", "/api/admin/articles", None),
        ("get", f"/api/admin/articles/{slug}", None),
        ("post", "/api/admin/articles", _article()),
        ("patch", f"/api/admin/articles/{slug}", {"read_minutes": 9}),
        ("post", f"/api/admin/articles/{slug}/publish", None),
        ("post", f"/api/admin/articles/{slug}/unpublish", None),
        ("post", f"/api/admin/articles/{SEEDED[0]['slug']}/unpublish", None),
    ]
    for method, url, body in calls:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url
        assert getattr(client, method)(url, headers=patient, **kwargs).status_code == 403, url
        assert getattr(client, method)(url, headers=staff, **kwargs).status_code == 403, url
    after = client.get(f"/api/admin/articles/{slug}", headers=admin_headers).json()
    assert (after["read_minutes"], after["is_published"]) == (5, False)
    assert client.get(f"/api/articles/{SEEDED[0]['slug']}").status_code == 200


# --- Publishing ---------------------------------------------------------------------------------


def _public_slugs(client, **params):
    return {a["slug"] for a in client.get("/api/articles", params=params).json()}


def test_drafts_are_hidden_from_every_public_view(client, admin_headers):
    draft = _create(client, admin_headers, title="Draft guidance on fertility testing", category="Fertility drafts")
    slug = draft["slug"]
    assert slug not in _public_slugs(client)
    assert slug not in _public_slugs(client, q="fertility testing")
    assert slug not in _public_slugs(client, category="Fertility drafts")
    missing = client.get(f"/api/articles/{slug}")
    assert missing.status_code == 404
    assert missing.json() == client.get("/api/articles/never-existed").json()  # a draft looks like a missing article
    # administrators still see it
    assert slug in {a["slug"] for a in client.get("/api/admin/articles", headers=admin_headers).json()}


def test_publish_and_unpublish(client, admin_headers):
    created = _create(client, admin_headers, title="Postnatal check-ups after birth", category="Pregnancy")
    slug = created["slug"]

    published = client.post(f"/api/admin/articles/{slug}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["updated_on"] == created["updated_on"]  # publishing is not a content edit
    assert slug in _public_slugs(client) and slug in _public_slugs(client, q="postnatal check-ups")
    assert slug in _public_slugs(client, category="Pregnancy")
    public = client.get(f"/api/articles/{slug}").json()
    assert set(public) == PUBLIC_DETAIL_KEYS  # no is_published in public responses
    assert all(set(a) == PUBLIC_LIST_KEYS for a in client.get("/api/articles").json())
    # publishing twice is harmless
    assert client.post(f"/api/admin/articles/{slug}/publish", headers=admin_headers).json()["is_published"] is True

    unpublished = client.post(f"/api/admin/articles/{slug}/unpublish", headers=admin_headers)
    assert unpublished.status_code == 200 and unpublished.json()["is_published"] is False
    assert slug not in _public_slugs(client)
    assert client.get(f"/api/articles/{slug}").status_code == 404
    # nothing was deleted: the content is intact and can be published again
    kept = client.get(f"/api/admin/articles/{slug}", headers=admin_headers).json()
    assert {k: v for k, v in kept.items() if k != "is_published"} == {k: v for k, v in created.items() if k != "is_published"}
    client.post(f"/api/admin/articles/{slug}/publish", headers=admin_headers)
    assert client.get(f"/api/articles/{slug}").json()["summary"] == created["summary"]


def test_unknown_article_cannot_be_published(client, admin_headers):
    assert client.post("/api/admin/articles/no-such-article/publish", headers=admin_headers).status_code == 404
    assert client.post("/api/admin/articles/no-such-article/unpublish", headers=admin_headers).status_code == 404


def test_seeded_articles_are_published_and_can_be_hidden_and_restored(client, admin_headers):
    listed = {a["slug"]: a for a in client.get("/api/admin/articles", headers=admin_headers).json()}
    assert all(listed[a["slug"]]["is_published"] is True for a in SEEDED)

    seeded = SEEDED[2]["slug"]
    before = client.get(f"/api/articles/{seeded}").json()
    assert client.post(f"/api/admin/articles/{seeded}/unpublish", headers=admin_headers).status_code == 200
    assert seeded not in _public_slugs(client)
    assert client.get(f"/api/articles/{seeded}").status_code == 404
    assert client.post(f"/api/admin/articles/{seeded}/publish", headers=admin_headers).status_code == 200
    assert client.get(f"/api/articles/{seeded}").json() == before  # restored exactly
