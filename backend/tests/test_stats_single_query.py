"""/api/stats returns the same counts as separate queries, in a single database round trip."""

from sqlalchemy import event, func, select

from app.database.session import SessionLocal, engine
from app.models import Facility, Service


def test_stats_counts_match_and_use_one_query(client, make_facility):
    make_facility(facility_type="laboratory", is_demo=False)
    make_facility(is_demo=True)
    statements = []
    listener = lambda *args: statements.append(args[2])  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        body = client.get("/api/stats").json()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    with SessionLocal() as db:
        assert body["facilities"] == db.scalar(select(func.count()).select_from(Facility))
        assert body["facilities_demo"] == db.scalar(select(func.count()).select_from(Facility).where(Facility.is_demo.is_(True)))
        assert body["laboratories"] == db.scalar(select(func.count()).select_from(Facility).where(Facility.facility_type == "laboratory"))
        assert body["towns"] == db.scalar(select(func.count(func.distinct(Facility.town))))
        assert body["services"] == db.scalar(select(func.count()).select_from(Service))
    assert set(body) == {"facilities", "facilities_demo", "registry_matched", "practitioners", "laboratories",
                         "upcoming_programs", "published_reviews", "towns", "services"}
    assert len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) == 1
