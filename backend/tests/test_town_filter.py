"""Town filter on Find Care. TEST FIXTURES only, in the disposable test database.

/api/towns?county=X lists the towns of one county, whatever spelling the county was imported with
("Wilaya ya Kisumu", "Kisumu County"), and folds case/space variants of the same town in that county together.
A town of the same name in another county stays separate, and the facility search matches the town the same way.
"""


def test_towns_for_one_county_fold_spellings_but_not_other_counties(client, make_facility):
    for town, county in (("Kisumu", "Kisumu"), ("Kisumu", "Wilaya ya Kisumu"), (" kisumu ", "Kisumu County"), ("Maseno", "Kisumu"),
                         ("Kisumu", "Busia"), ("Townfixture", "Nakuru")):
        make_facility(name=f"Townfixture {town} {county}", town=town, county=county)

    towns = {t["town"]: t["facility_count"] for t in client.get("/api/towns", params={"county": "Kisumu"}).json()}
    assert towns["Kisumu"] >= 3 and towns["Maseno"] >= 1
    assert " kisumu " not in towns and "Townfixture" not in towns
    assert all(t["county"] == "Kisumu" for t in client.get("/api/towns", params={"county": "Kisumu"}).json())

    # without a county the existing list keeps its shape for the other pages
    assert {"town", "county", "facility_count", "latitude", "longitude"} <= set(client.get("/api/towns").json()[0])

    names = lambda **p: {f["name"] for f in client.get("/api/facilities", params={"page_size": 40, "q": "Townfixture", **p}).json()["items"]}
    in_kisumu = names(county="Kisumu", town="Kisumu")
    assert {"Townfixture Kisumu Kisumu", "Townfixture Kisumu Wilaya ya Kisumu", "Townfixture  kisumu  Kisumu County"} <= in_kisumu
    assert "Townfixture Kisumu Busia" not in in_kisumu and "Townfixture Maseno Kisumu" not in in_kisumu
    assert "Townfixture Kisumu Busia" in names(county="Busia", town="Kisumu")
    # a town name in the search box still finds facilities by town
    assert "Townfixture Maseno Kisumu" in names(q="Maseno")
