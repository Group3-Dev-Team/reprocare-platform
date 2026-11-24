"""Search, filters, sorting, pagination, details and reference data.

The tests create their own directory of facilities (conftest.py: feature tests do not rely on demo seed data)
and scope whole-list assertions to it with `q=dirtest`, so other test files' records cannot change the results.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, select

from app.database.session import SessionLocal
from app.models import DataSource, Facility, FacilityExternalProfile, Insurer, LabTest, Practitioner, Review, Service, User
from app.services import facility_service

TOKEN = "dirtest"  # in every directory facility's description, so `q=dirtest` selects exactly this dataset
NAIROBI, KISUMU = (-1.2864, 36.8172), (-0.0917, 34.7680)
FILLER = 39
SEEDED_ARTICLES = json.loads((Path(__file__).parents[1] / "app" / "database" / "reference_data.json").read_text())["articles"]


@pytest.fixture(scope="module")
def directory():
    """Demonstration facilities with the services, insurers, hours, reviews, lab tests and practitioners the tests need."""
    with SessionLocal() as db:
        services = {s.slug: s for s in db.scalars(select(Service))}
        sha = db.scalar(select(Insurer).where(Insurer.slug == "sha"))
        source = db.scalar(select(DataSource).where(DataSource.code == "reprocare_bot"))

        def facility(slug, name, town, county, coords, kind="clinic", offers=(), **fields):
            f = Facility(
                slug=slug, name=name, facility_type=kind, town=town, county=county,
                latitude=coords[0] if coords else None, longitude=coords[1] if coords else None,
                description=f"Directory test facility ({TOKEN}).", is_demo=True, **fields,
            )
            f.services = [services[s] for s in offers]
            db.add(f)
            return f

        mwangaza = facility("dir-mwangaza", "Mwangaza Family Health Centre", "Nairobi", "Nairobi", NAIROBI, offers=["antenatal", "cervical"],
                            registration_status="matched", source_id=source.id, open_weekends=True,
                            weekday_hours="8:00 AM – 5:00 PM", saturday_hours="9:00 AM – 1:00 PM", sunday_hours="Closed")
        mwangaza.insurers = [sha]
        kipepeo = facility("dir-kipepeo", "Kipepeo Maternity Home", "Kisumu", "Kisumu", KISUMU, kind="maternity_home", offers=["maternity"],
                           open_24_hours=True, weekday_hours="Open 24 hours")
        facility("dir-kisumu-unmapped", "Lakeside Outreach Point", "Kisumu", "Kisumu", None)
        facility("dir-hospital", "Uhuru Referral Hospital", "Nairobi", "Nairobi City", NAIROBI, kind="hospital", open_24_hours=True)
        labs = [facility(f"dir-lab-{i}", f"Afya Diagnostics {i}", "Nairobi", "Nairobi", NAIROBI, kind="laboratory", offers=["lab"]) for i in range(3)]
        for i in range(FILLER - 3):
            facility(f"dir-filler-{i:02d}", f"Directory Clinic {i:02d}", "Nairobi", "Nairobi County", NAIROBI, weekday_hours="By appointment")
        db.flush()

        db.add_all([
            LabTest(facility_id=labs[0].id, name="HIV viral load"), LabTest(facility_id=labs[1].id, name="HIV rapid test"),
            LabTest(facility_id=labs[2].id, name="Full blood count"),
        ])
        db.add_all([
            Practitioner(slug="dir-wekesa", full_name="Grace Wekesa", title="Midwife", specialty="Midwifery", town="Kisumu", facility_id=kipepeo.id, is_demo=True),
            Practitioner(slug="dir-otieno", full_name="Dr Paul Otieno", title="Gynaecologist", specialty="Obstetrics & gynaecology", town="Nairobi",
                         facility_id=mwangaza.id, is_demo=True),
        ])
        # "!" is not a bcrypt hash, so nobody can sign in as this reviewer
        reviewer = User(email=f"{TOKEN}-reviewer@example.com", full_name="Directory Reviewer", role="patient", password_hash="!")
        db.add(reviewer)
        db.flush()
        for facility_row, ratings in ((mwangaza, [5, 4, 4]), (kipepeo, [3]), (labs[0], [2, 3])):
            for rating in ratings:
                db.add(Review(facility_id=facility_row.id, user_id=reviewer.id, author_name="Reviewer", rating=rating, title="Visit",
                              body="A directory test review of this facility.", status="published", is_demo=True))
        db.add(Review(facility_id=labs[1].id, user_id=reviewer.id, author_name="Reviewer", rating=5, title="Pending", body="Not yet moderated review.", status="pending"))
        db.commit()
    yield
    with SessionLocal.begin() as db:
        ids = select(Facility.id).where(Facility.slug.like("dir-%"))
        db.execute(delete(Practitioner).where(Practitioner.slug.like("dir-%")))
        db.execute(delete(Facility).where(Facility.id.in_(ids)))  # reviews and lab tests cascade
        db.execute(delete(User).where(User.email == f"{TOKEN}-reviewer@example.com"))


pytestmark = pytest.mark.usefixtures("directory")
DATASET = 4 + 3 + (FILLER - 3)  # named facilities + laboratories + filler = 43


def scoped(client, path="/api/facilities", **params):
    return client.get(path, params={"q": TOKEN, **params}).json()


def test_default_page_holds_40_and_paginates(client):
    default = client.get("/api/facilities").json()
    assert default["page_size"] == 40
    assert len(default["items"]) == 40

    first = scoped(client, page=1, page_size=15)
    assert first["total"] == DATASET
    assert first["page_size"] == 15
    assert first["pages"] == math.ceil(DATASET / 15)

    slugs = []
    for page in range(1, first["pages"] + 1):
        response = client.get("/api/facilities", params={"q": TOKEN, "page": page, "page_size": 15})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == page
        assert len(data["items"]) == min(15, DATASET - 15 * (page - 1))
        slugs.extend(f["slug"] for f in data["items"])

    assert len(slugs) == DATASET
    assert len(set(slugs)) == DATASET


def test_page_size_is_capped_at_40(client):
    assert client.get("/api/facilities?page_size=100").status_code == 422


def test_service_filter_matches_real_data(client):
    data = client.get("/api/facilities?service=cervical").json()
    assert data["total"] > 0
    assert all(any(s["slug"] == "cervical" for s in f["services"]) for f in data["items"])
    assert "dir-mwangaza" in {f["slug"] for f in scoped(client, service="cervical")["items"]}


def test_kiswahili_keyword_search_finds_service(client):
    data = client.get("/api/facilities?q=mimba").json()  # "mimba" is a keyword for antenatal care
    assert data["total"] > 0
    assert all(any(s["slug"] == "antenatal" for s in f["services"]) or "mimba" in f["name"].lower() for f in data["items"])
    assert "dir-mwangaza" in {f["slug"] for f in data["items"]}


def test_combined_filters(client):
    data = client.get("/api/facilities?town=Nairobi&open_weekends=true&insurer=sha").json()
    assert data["total"] >= 1
    for f in data["items"]:
        assert f["town"] == "Nairobi" and f["open_weekends"] and any(i["slug"] == "sha" for i in f["insurers"])


def test_type_filter_and_laboratories(client):
    data = scoped(client, facility_type="laboratory")
    assert data["total"] == 3 and all(f["facility_type"] == "laboratory" for f in data["items"])
    tests = client.get("/api/lab-tests?q=hiv").json()
    assert tests["total"] >= 2 and all("hiv" in t["name"].lower() for t in tests["items"])


def test_no_results_returns_empty_list_not_fake_matches(client):
    data = client.get("/api/facilities?q=zzzz-no-such-place").json()
    assert data["total"] == 0 and data["items"] == []


def test_distance_sort(client):
    data = scoped(client, lat=-0.09, lng=34.77, sort="distance", page_size=10)
    distances = [f["distance_km"] for f in data["items"]]
    assert distances == sorted(distances) and data["items"][0]["town"] == "Kisumu"
    assert "dir-kisumu-unmapped" not in {f["slug"] for f in data["items"]}  # no stored coordinates, no distance


def test_rating_sort_is_descending(client):
    items = client.get("/api/facilities?sort=rating&page_size=20").json()["items"]
    ratings = [f["rating"]["average"] or 0 for f in items]
    assert ratings == sorted(ratings, reverse=True)
    mine = [f for f in scoped(client, sort="rating")["items"] if f["rating"]["count"]]
    assert [f["slug"] for f in mine] == ["dir-mwangaza", "dir-kipepeo", "dir-lab-0"]  # 4.3, 3.0, 2.5; pending reviews ignored


def test_facility_detail_and_404(client):
    d = client.get("/api/facilities/dir-mwangaza").json()
    assert d["name"] == "Mwangaza Family Health Centre"
    assert d["registration"]["status"] == "matched" and d["source"]["code"] == "reprocare_bot" and d["is_demo"] is True
    assert [p["slug"] for p in d["practitioners"]] == ["dir-otieno"]
    assert client.get("/api/facilities/does-not-exist").status_code == 404


def test_markers_only_include_stored_coordinates(client):
    markers = scoped(client, "/api/facilities/markers", town="Kisumu")
    assert markers and all(m["latitude"] is not None and m["longitude"] is not None for m in markers)
    assert "dir-kipepeo" in {m["slug"] for m in markers} and "dir-kisumu-unmapped" not in {m["slug"] for m in markers}


def test_practitioners(client):
    data = client.get("/api/practitioners", params={"page_size": 40}).json()
    listed = {p["slug"]: p for p in data["items"]}
    assert {"dir-wekesa", "dir-otieno"} <= set(listed)
    assert listed["dir-wekesa"]["is_demo"] and listed["dir-otieno"]["is_demo"]
    midwives = client.get("/api/practitioners?specialty=Midwifery").json()
    assert midwives["total"] >= 1 and all(p["specialty"] == "Midwifery" for p in midwives["items"])
    assert client.get("/api/practitioners/dir-wekesa").json()["facility"]["slug"] == "dir-kipepeo"
    assert any(s["name"] == "Midwifery" and s["count"] >= 1 for s in client.get("/api/practitioners/specialties").json())


def test_reference_lists_and_stats(client, make_facility):
    assert len(client.get("/api/services").json()) == 11
    assert any(i["slug"] == "sha" for i in client.get("/api/insurers").json())
    before = client.get("/api/stats").json()
    assert before["facilities"] >= DATASET and before["facilities_demo"] >= DATASET
    make_facility(is_demo=True)
    make_facility(is_demo=False)
    after = client.get("/api/stats").json()
    assert after["facilities"] == before["facilities"] + 2
    assert after["facilities_demo"] == before["facilities_demo"] + 1


def test_articles(client):
    listed = {a["slug"] for a in client.get("/api/articles").json()}
    assert {a["slug"] for a in SEEDED_ARTICLES} <= listed  # other features may add articles
    full = client.get("/api/articles/cervical-screening").json()
    assert full["sections"] and full["references"]


def test_county_alias_and_sort_order_match_directory_and_map(client):
    canonical = scoped(client, county="Nairobi", sort="name_desc")
    legacy = scoped(client, county="Wilaya ya Nairobi", sort="name_desc")
    markers = scoped(client, "/api/facilities/markers", county="Wilaya ya Nairobi", sort="name_desc")
    assert canonical["total"] == legacy["total"] == len(markers) > 0
    assert [item["slug"] for item in legacy["items"]] == [item["slug"] for item in canonical["items"]]
    assert [item["slug"] for item in legacy["items"]] == [item["slug"] for item in markers][: len(legacy["items"])]
    names = [item["name"].lower() for item in legacy["items"]]
    assert names == sorted(names, reverse=True)

    reviewed = scoped(client, has_patient_reviews=True, sort="review_count")
    counts = [item["rating"]["count"] for item in reviewed["items"]]
    assert counts and all(count > 0 for count in counts)
    assert counts == sorted(counts, reverse=True)


def test_google_discovery_uses_latest_snapshot_before_filtering(client):
    fixtures = [
        ("dir-mwangaza", "directory-google-old", 5.0, 900, 2020),
        ("dir-mwangaza", "directory-google-current", 3.0, 100, 2025),
        ("dir-kipepeo", "directory-google-other", 4.5, 200, 2025),
    ]
    try:
        with SessionLocal.begin() as db:
            for slug, external_id, rating, count, year in fixtures:
                facility_id = db.scalar(select(Facility.id).where(Facility.slug == slug))
                db.add(FacilityExternalProfile(
                    facility_id=facility_id, platform="google", external_id=external_id,
                    rating=rating, rating_count=count, fetched_at=datetime(year, 1, 1, tzinfo=timezone.utc),
                ))
        params = {"has_google_rating": True, "sort": "google_count"}
        response = scoped(client, **params)
        ordered = [row for row in response["items"] if row["slug"] in {"dir-mwangaza", "dir-kipepeo"}]
        assert [row["slug"] for row in ordered] == ["dir-kipepeo", "dir-mwangaza"]
        assert ordered[1]["google_rating"]["rating"] == 3.0
        params.update(min_google_rating=4.0, sort="google_rating")
        listing = scoped(client, **params)
        markers = scoped(client, "/api/facilities/markers", **params)
        included = {row["slug"] for row in listing["items"]}
        assert included == {row["slug"] for row in markers}
        assert "dir-kipepeo" in included and "dir-mwangaza" not in included
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(FacilityExternalProfile).where(FacilityExternalProfile.external_id.in_([row[1] for row in fixtures])))


def test_facility_type_filter_ignores_case(client):
    lower = client.get("/api/facilities", params={"facility_type": "hospital"}).json()["total"]
    assert lower > 0
    assert client.get("/api/facilities", params={"facility_type": "Hospital"}).json()["total"] == lower
    assert client.get("/api/facilities", params={"facility_type": "HOSPITAL,Clinic"}).json()["total"] >= lower


def test_county_spellings_resolve_to_the_same_results(client):
    from app.services.county_service import county_filter_labels, county_key

    assert county_key("Nairobi City") == "nairobi"
    assert county_key("Nairobi City County") == "nairobi"
    assert county_key("Kiambu County") == "kiambu"
    assert county_key("  Taita  Taveta ") == "taita-taveta"
    assert county_key("Kaunti ya Murang'a") == "murang'a"
    assert county_key("Somewhere Else") == "somewhere else"  # unmatched text is preserved
    assert "nairobi city" in county_filter_labels("Nairobi") and "kiambu county" in county_filter_labels("Kiambu")

    base = client.get("/api/facilities", params={"county": "Nairobi"}).json()["total"]
    assert base > 0
    for spelling in ("Nairobi City", "Nairobi County", "nairobi"):
        assert client.get("/api/facilities", params={"county": spelling}).json()["total"] == base


# --- Open now (SCRUM-9) ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hours, minute, expected",
    [
        ("9:00 AM – 5:00 PM", 9 * 60, True),  # Google Places format
        ("9:00 AM – 5:00 PM", 17 * 60, False),  # closing time is closed
        ("9:00 AM – 5:00 PM", 8 * 60 + 59, False),
        ("8:00 – 11:30 AM", 11 * 60, True),  # the period applies to both times
        ("08:00-17:00", 16 * 60 + 59, True),  # 24-hour clock
        ("6:00 PM – 6:00 AM", 2 * 60, True),  # past midnight
        ("6:00 PM – 6:00 AM", 12 * 60, False),
        ("12:00 AM – 12:00 PM", 0, True),
        ("Open 24 hours", 3, True),
        ("Closed", 10 * 60, False),
        ("By appointment", 10 * 60, None),  # unreadable hours are never guessed
        ("", 10 * 60, None),
        ("25:00-26:00", 0, None),
    ],
)
def test_opening_hours_are_read_without_guessing(hours, minute, expected):
    assert facility_service.open_at(hours, minute) is expected


def _at(monkeypatch, year, month, day, hour, minute=0):
    moment = datetime(year, month, day, hour, minute, tzinfo=facility_service.KENYA_TIME)
    monkeypatch.setattr(facility_service, "_kenya_now", lambda: moment)


def _open_now(client):
    listing = {f["slug"] for f in scoped(client, open_now=True)["items"]}
    markers = {m["slug"] for m in scoped(client, "/api/facilities/markers", open_now=True)}
    return listing, markers


def test_open_now_uses_todays_hours_in_kenya_time(client, monkeypatch):
    _at(monkeypatch, 2026, 11, 24, 10)  # Tuesday 10:00
    listing, markers = _open_now(client)
    assert listing == {"dir-mwangaza", "dir-kipepeo", "dir-hospital"}  # weekday hours, "Open 24 hours" text, 24-hour flag
    assert markers == listing  # the map shows the same facilities as the list

    _at(monkeypatch, 2026, 11, 24, 18)  # Tuesday 18:00: Mwangaza has closed
    assert _open_now(client)[0] == {"dir-kipepeo", "dir-hospital"}

    _at(monkeypatch, 2026, 11, 28, 12)  # Saturday 12:00 uses Saturday hours
    assert "dir-mwangaza" in _open_now(client)[0]
    _at(monkeypatch, 2026, 11, 29, 12)  # Sunday: "Closed"
    assert "dir-mwangaza" not in _open_now(client)[0]


def test_open_now_leaves_out_unknown_hours_and_combines_with_filters(client, monkeypatch):
    _at(monkeypatch, 2026, 11, 24, 10)
    listing, _ = _open_now(client)
    assert not any(slug.startswith(("dir-filler-", "dir-lab-")) for slug in listing)  # "By appointment" or no hours
    assert {f["slug"] for f in scoped(client, open_now=True, town="Kisumu")["items"]} == {"dir-kipepeo"}
    assert scoped(client, open_now=False)["total"] == DATASET  # the filter is off unless asked for
