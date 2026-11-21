"""Bot tests. Everything here uses TEST FIXTURES in the isolated test database and a temporary bot folder.
No network calls are made: Google Places, Apify and Facebook are replaced by recorded-shape fixtures."""

import os
import sys
import tempfile
from pathlib import Path

BOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://reprocare:reprocare@localhost:5432/reprocare_test")
os.environ["APP_ENV"] = "test"
os.environ["REPROCARE_BOT_HOME"] = tempfile.mkdtemp(prefix="reprocare-bot-test-")
os.environ["GOOGLE_PLACES_API_KEY"] = ""
os.environ["APIFY_API_TOKEN"] = ""
sys.path.insert(0, str(BOT))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    from app.database.init_db import create_tables
    from app.database.seed_reference import load_reference
    from app.database.session import SessionLocal
    from app.database.test_safety import assert_disposable_database

    assert_disposable_database(os.environ["DATABASE_URL"])
    create_tables(reset=True)
    with SessionLocal() as db:
        load_reference(db)
    yield


@pytest.fixture()
def db():
    from app.database.session import SessionLocal

    with SessionLocal() as session:
        yield session
