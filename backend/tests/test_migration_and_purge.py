"""Migration of the integration build's `external_feedback` table, and removal of the fictional seed.

Runs against a SEPARATE scratch database (TEST_SCRATCH_DATABASE_URL) because it resets that database.
Every record inserted here is a labelled test fixture.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

SCRATCH = os.environ.get("TEST_SCRATCH_DATABASE_URL")
BACKEND = Path(__file__).resolve().parents[1]
LEGACY_DDL = BACKEND / "tests" / "fixtures" / "legacy_external_feedback.sql"

pytestmark = [
    pytest.mark.skipif(not SCRATCH, reason="set TEST_SCRATCH_DATABASE_URL to run migration tests"),
    pytest.mark.skipif(importlib.util.find_spec("app.database.seed") is None, reason="needs the demo seed (integration test)"),
]


def run(*args):
    env = {**os.environ, "DATABASE_URL": SCRATCH, "APP_ENV": "development"}
    out = subprocess.run([sys.executable, "-m", *args], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout


def test_legacy_migration_then_purge():
    from app.database.test_safety import assert_disposable_database

    assert_disposable_database(SCRATCH)
    engine = create_engine(SCRATCH)
    with engine.begin() as db:  # leftovers from a previous run reference facilities; clear them first
        db.execute(text("DROP TABLE IF EXISTS schema_migrations, external_feedback, external_google_ratings"))
    run("app.database.seed", "--reset")  # simulates the original application database (fictional seed)
    with engine.begin() as db:
        db.execute(text("DROP TABLE IF EXISTS schema_migrations, external_feedback, external_google_ratings"))
        db.execute(text("DELETE FROM external_comments; DELETE FROM external_posts; DELETE FROM facility_external_profiles"))
        db.execute(text(LEGACY_DDL.read_text()))
        real = db.scalar(text(
            "INSERT INTO facilities (slug, name, facility_type, description, address, area, town, county, phone, email, website, weekday_hours, saturday_hours, "
            "sunday_hours, open_24_hours, open_weekends, languages, payment_methods, accessibility, offers_telehealth, accepts_appointment_requests, "
            "registration_status, registration_body, registration_code, image_key, is_demo, external_id) VALUES "
            "('fixture-real-hospital', 'Fixture Real Hospital', 'hospital', '', '', '', 'Nairobi', 'Nairobi', '', '', '', '', '', '', false, false, '', '', '', "
            "false, false, 'not_checked', '', '', '', false, 'fixture-place') RETURNING id"))
        db.execute(text("""
            INSERT INTO external_feedback (facility_id, facility_name, platform, external_id, source_url, original_text, classification, collected_at) VALUES
            (NULL, 'fixture real HOSPITAL', 'facebook', 'fx1', 'https://web.facebook.com/fixture/posts/pfbidA', 'Test fixture: kind nurses', 'unverified_comment_candidate', now()),
            (NULL, 'Fixture Real Hospital', 'facebook', 'fx2', 'https://web.facebook.com/fixture/posts/pfbidA', 'Test fixture: long queue at reception', 'unverified_comment_candidate', now()),
            (NULL, 'Fixture Real Hospital', 'tiktok', '7000000000000000001', 'https://www.tiktok.com/@fixture/video/7000000000000000001', 'Test fixture tiktok comment', 'unverified_comment_candidate', '2026-01-02T10:00:00Z'),
            (NULL, 'Unknown Fixture Clinic', 'facebook', 'fx3', 'https://web.facebook.com/other/posts/pfbidB', 'Test fixture: unlinked', 'unverified_comment_candidate', now()),
            (NULL, 'Fixture Real Hospital', 'google_maps', 'gfx1', 'https://www.google.com/maps/reviews/fixture', 'Test fixture google review', 'unverified_external_review', now())
        """))
        db.execute(text("INSERT INTO external_google_ratings VALUES ('gfx1', 'fixture-place', 2)"))
        rating_before = db.execute(text("SELECT count(*) FROM reviews")).scalar()

    out = run("app.database.migrate")
    assert "0002_migrate_integration_feedback" in out
    assert "Database is up to date" in run("app.database.migrate")  # idempotent

    with engine.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM external_feedback")) == 5  # legacy table untouched
        assert db.scalar(text("SELECT count(*) FROM external_comments WHERE facility_id = :f"), {"f": real}) == 4
        assert db.scalar(text("SELECT count(*) FROM external_posts WHERE facility_id IS NULL")) == 1
        assert db.scalar(text("SELECT source_rating FROM external_comments WHERE external_id = 'gfx1'")) == 2
        assert db.scalar(text("SELECT published_at IS NOT NULL FROM external_comments WHERE platform = 'tiktok'"))
        assert db.scalar(text("SELECT count(*) FROM facility_external_profiles WHERE platform='google' AND external_id='fixture-place'")) == 1
        assert db.scalar(text("SELECT count(*) FROM reviews")) == rating_before

    run("app.database.purge_demo", "--yes")
    with engine.begin() as db:
        assert db.scalar(text("SELECT count(*) FROM facilities WHERE is_demo")) == 0
        assert db.scalar(text("SELECT count(*) FROM reviews WHERE is_demo")) == 0
        assert db.scalar(text("SELECT count(*) FROM users WHERE email LIKE '%@reprocare.demo'")) == 0
        assert db.scalar(text("SELECT count(*) FROM facilities WHERE slug = 'fixture-real-hospital'")) == 1
        assert db.scalar(text("SELECT count(*) FROM external_comments WHERE facility_id = :f"), {"f": real}) == 4
        assert db.scalar(text("SELECT count(*) FROM services")) > 0  # reference data kept

    run("app.database.seed_reference")  # safe on an existing database
    engine.dispose()
