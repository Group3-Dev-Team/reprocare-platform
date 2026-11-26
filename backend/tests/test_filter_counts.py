"""Search filters, option counts and labelled alternatives. TEST FIXTURES only, in the disposable test database.

A county or town count shown next to an active search is the number of facilities matching that search there,
not the county total (the "Machakos (26)" then zero results report). A facility without recorded services is
never a match for a service, but a zero-result service search says how many facilities in the same area have no
services recorded yet, so they can be offered as clearly labelled places to ask.
"""

import itertools

import pytest

TAG = "Filtfix"
_run = itertools.count()


@pytest.fixture()
def fixtures(make_facility):
    global TAG
    TAG = f"Filtfix{next(_run)}x"
    rows = [
        ("Machakos", "Machakos", "clinic", ["hiv"]),
        ("Machakos", "Athi River", "hospital", []),
        ("Machakos", "Athi River", "hospital", []),
        ("Kisumu", "Kisumu", "hospital", ["gynae", "antenatal"]),
        ("Kisumu", "Maseno", "clinic", ["hiv"]),
        ("Mombasa", "Mombasa", "hospital", []),
        ("Nairobi", "Nairobi", "hospital", ["gynae", "hiv"]),
        ("Nairobi", "Nairobi", "laboratory", ["lab"]),
    ]
    for i, (county, town, kind, services) in enumerate(rows):
        make_facility(name=f"{TAG} {county} {town} {i}", county=county, town=town, facility_type=kind, services=services)


def total(client, **params):
    return client.get("/api/facilities", params={"q": TAG, "page_size": 1, **params}).json()


def counties(client, **params):
    return {c["county"]: c for c in client.get("/api/counties", params={"q": TAG, **params}).json()}


@pytest.mark.parametrize("params, expected", [
    ({}, 8),
    ({"service": "hiv"}, 3),
    ({"service": "hiv", "county": "Machakos"}, 1),
    ({"service": "hiv", "county": "Kisumu"}, 1),
    ({"service": "gynae", "county": "Mombasa"}, 0),
    ({"service": "antenatal", "county": "Mombasa"}, 0),
    ({"service": "gynae", "county": "Nairobi"}, 1),
    ({"service": "hiv", "county": "Kisumu", "town": "Maseno"}, 1),
    ({"service": "hiv", "county": "Kisumu", "town": "Maseno", "facility_type": "hospital"}, 0),
    ({"service": "gynae", "county": "Kisumu", "facility_type": "hospital", "sort": "name"}, 1),
    ({"facility_type": "laboratory", "county": "Nairobi"}, 1),
    ({"county": "Machakos", "no_recorded_services": "true"}, 2),
])
def test_single_and_combined_filters(client, fixtures, params, expected):
    assert total(client, **params)["total"] == expected


def test_county_counts_follow_the_other_active_filters(client, fixtures):
    hiv = counties(client, service="hiv")
    assert hiv["Machakos"]["facility_count"] == 1 and hiv["Machakos"]["contextual"] is True
    assert hiv["Mombasa"]["facility_count"] == 0
    assert hiv["Machakos"]["total_count"] >= 3  # every facility in the county, not only these fixtures
    # the count shown is what the search returns
    for county in ("Machakos", "Kisumu", "Mombasa", "Nairobi"):
        assert hiv[county]["facility_count"] == total(client, service="hiv", county=county)["total"]
    # a selected county does not narrow the county list itself
    assert counties(client, service="hiv", county="Kisumu")["Machakos"]["facility_count"] == 1


def test_counts_without_context_are_county_totals(client, fixtures):
    plain = {c["county"]: c for c in client.get("/api/counties").json()}
    assert plain["Machakos"]["contextual"] is False
    assert plain["Machakos"]["facility_count"] == plain["Machakos"]["total_count"] >= 3
    assert len(plain) == 47


def test_town_counts_follow_the_other_active_filters(client, fixtures):
    towns = {t["town"]: t for t in client.get("/api/towns", params={"county": "Machakos", "q": TAG, "service": "hiv"}).json()}
    assert towns["Machakos"]["facility_count"] == 1
    assert towns["Athi River"]["facility_count"] == 0 and towns["Athi River"]["contextual"] is True
    # a selected town does not narrow the town list itself
    again = {t["town"]: t for t in client.get("/api/towns", params={"county": "Machakos", "q": TAG, "service": "hiv", "town": "Machakos"}).json()}
    assert again["Athi River"]["total_count"] == towns["Athi River"]["total_count"]


def test_zero_service_results_report_unrecorded_alternatives_without_inventing_matches(client, fixtures):
    result = total(client, service="gynae", county="Mombasa")
    assert result["total"] == 0 and result["items"] == []
    assert result["unrecorded_service_alternatives"] == 1
    # Machakos has one facility with services (hiv) and two without: only the two are alternatives
    assert total(client, service="gynae", county="Machakos")["unrecorded_service_alternatives"] == 2
    # results with matches, and searches without a service, carry no alternatives key
    assert "unrecorded_service_alternatives" not in total(client, service="hiv")
    assert "unrecorded_service_alternatives" not in total(client, county="Garissa")


def test_lab_tests_filter_by_county(client, make_facility):
    from app.database.session import SessionLocal
    from app.models import LabTest

    lab = make_facility(name=f"{TAG} Lab Nakuru", county="Nakuru", town="Naivasha", facility_type="laboratory")
    with SessionLocal() as db:
        db.add(LabTest(facility_id=lab.id, name=f"{TAG} hormone panel", sample_type="blood", turnaround="1 day", price_note="", home_collection=False))
        db.commit()
    names = lambda **p: {t["name"] for t in client.get("/api/lab-tests", params={"q": TAG, **p}).json()["items"]}
    assert names(county="Nakuru") == {f"{TAG} hormone panel"}
    assert names(county="Nakuru", town="naivasha ") == {f"{TAG} hormone panel"}
    assert names(county="Kisumu") == set()
