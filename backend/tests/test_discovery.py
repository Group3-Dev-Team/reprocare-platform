"""Search, filters, sorting, pagination, details and reference data against the seeded demo dataset."""


def test_default_page_holds_40_and_paginates(client):
    default = client.get("/api/facilities").json()
    assert default["page_size"] == 40
    assert len(default["items"]) == 40

    first = client.get("/api/facilities?page=1&page_size=15").json()
    assert first["total"] == 75
    assert first["page_size"] == 15
    assert first["pages"] == 5

    slugs = []
    for page in range(1, 6):
        response = client.get(f"/api/facilities?page={page}&page_size=15")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == page
        assert len(data["items"]) == 15
        slugs.extend(f["slug"] for f in data["items"])

    assert len(slugs) == 75
    assert len(set(slugs)) == 75


def test_page_size_is_capped_at_40(client):
    assert client.get("/api/facilities?page_size=100").status_code == 422


def test_service_filter_matches_real_data(client):
    data = client.get("/api/facilities?service=cervical").json()
    assert data["total"] > 0
    assert all(any(s["slug"] == "cervical" for s in f["services"]) for f in data["items"])


def test_kiswahili_keyword_search_finds_service(client):
    data = client.get("/api/facilities?q=mimba").json()  # "mimba" is a keyword for antenatal care
    assert data["total"] > 0
    assert all(any(s["slug"] == "antenatal" for s in f["services"]) or "mimba" in f["name"].lower() for f in data["items"])


def test_combined_filters(client):
    data = client.get("/api/facilities?town=Nairobi&open_weekends=true&insurer=sha").json()
    for f in data["items"]:
        assert f["town"] == "Nairobi" and f["open_weekends"] and any(i["slug"] == "sha" for i in f["insurers"])


def test_type_filter_and_laboratories(client):
    data = client.get("/api/facilities?facility_type=laboratory").json()
    assert data["total"] >= 10 and all(f["facility_type"] == "laboratory" for f in data["items"])
    tests = client.get("/api/lab-tests?q=hiv").json()
    assert tests["total"] > 0 and all("hiv" in t["name"].lower() for t in tests["items"])


def test_no_results_returns_empty_list_not_fake_matches(client):
    data = client.get("/api/facilities?q=zzzz-no-such-place").json()
    assert data["total"] == 0 and data["items"] == []


def test_distance_sort(client):
    data = client.get("/api/facilities?lat=-0.09&lng=34.77&sort=distance&page_size=10").json()
    distances = [f["distance_km"] for f in data["items"]]
    assert distances == sorted(distances) and data["items"][0]["town"] == "Kisumu"


def test_rating_sort_is_descending(client):
    items = client.get("/api/facilities?sort=rating&page_size=20").json()["items"]
    ratings = [f["rating"]["average"] or 0 for f in items]
    assert ratings == sorted(ratings, reverse=True)


def test_facility_detail_and_404(client):
    d = client.get("/api/facilities/mwangaza").json()
    assert d["name"] == "Mwangaza Family Health Centre"
    assert d["registration"]["status"] == "matched" and d["source"]["code"] == "demo" and d["is_demo"] is True
    assert client.get("/api/facilities/does-not-exist").status_code == 404


def test_markers_only_include_stored_coordinates(client):
    markers = client.get("/api/facilities/markers?town=Kisumu").json()
    assert markers and all(m["latitude"] is not None and m["longitude"] is not None for m in markers)


def test_practitioners(client):
    data = client.get("/api/practitioners").json()
    assert data["total"] == 15 and len(data["items"]) == 15
    assert all(p["is_demo"] for p in data["items"])
    midwives = client.get("/api/practitioners?specialty=Midwifery").json()
    assert all(p["specialty"] == "Midwifery" for p in midwives["items"])
    assert client.get("/api/practitioners/wekesa").json()["facility"]["slug"] == "kipepeo"
    assert client.get("/api/practitioners/specialties").json()


def test_reference_lists_and_stats(client):
    assert len(client.get("/api/services").json()) == 11
    assert any(i["slug"] == "sha" for i in client.get("/api/insurers").json())
    stats = client.get("/api/stats").json()
    assert stats["facilities"] == 75
    assert stats["facilities_demo"] == 75


def test_articles(client):
    articles = client.get("/api/articles").json()
    assert len(articles) == 8
    full = client.get("/api/articles/cervical-screening").json()
    assert full["sections"] and full["references"]



def test_county_alias_and_sort_order_match_directory_and_map(client):
    canonical = client.get("/api/facilities", params={"county": "Nairobi", "sort": "name_desc"}).json()
    legacy = client.get("/api/facilities", params={"county": "Wilaya ya Nairobi", "sort": "name_desc"}).json()
    markers = client.get("/api/facilities/markers", params={"county": "Wilaya ya Nairobi", "sort": "name_desc"}).json()
    assert canonical["total"] == legacy["total"] == len(markers)
    assert [item["slug"] for item in legacy["items"]] == [item["slug"] for item in canonical["items"]]
    assert [item["slug"] for item in legacy["items"]] == [item["slug"] for item in markers]
    names = [item["name"].lower() for item in legacy["items"]]
    assert names == sorted(names, reverse=True)

    reviewed = client.get("/api/facilities", params={"has_patient_reviews": True, "sort": "review_count"}).json()
    counts = [item["rating"]["count"] for item in reviewed["items"]]
    assert counts and all(count > 0 for count in counts)
    assert counts == sorted(counts, reverse=True)


def test_google_discovery_uses_latest_snapshot_before_filtering(client):
    from datetime import datetime, timezone

    from sqlalchemy import delete, select

    from app.database.session import SessionLocal
    from app.models import Facility, FacilityExternalProfile

    fixtures = [
        ("mwangaza", "directory-google-old", 5.0, 900, 2020),
        ("mwangaza", "directory-google-current", 3.0, 100, 2025),
        ("kipepeo", "directory-google-other", 4.5, 200, 2025),
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
        response = client.get("/api/facilities", params=params).json()
        ordered = [row for row in response["items"] if row["slug"] in {"mwangaza", "kipepeo"}]
        assert [row["slug"] for row in ordered] == ["kipepeo", "mwangaza"]
        assert ordered[1]["google_rating"]["rating"] == 3.0
        params.update(min_google_rating=4.0, sort="google_rating")
        listing = client.get("/api/facilities", params=params).json()
        markers = client.get("/api/facilities/markers", params=params).json()
        included = {row["slug"] for row in listing["items"]}
        assert included == {row["slug"] for row in markers}
        assert "kipepeo" in included and "mwangaza" not in included
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
