"""Load PRODUCTION reference data and (optionally) create the first administrator.

    python -m app.database.seed_reference
    python -m app.database.seed_reference --admin-email you@example.com --admin-name "Your Name"
        (prompts for the password; never pass it on the command line)

Loads only: the service taxonomy, real insurers/schemes and the data sources
used by the bot. It never creates facilities, reviews, practitioners or programmes — facilities come
from the ReproCare bot (Google Places discovery) or the import API, reviews come from real patients.
Safe to run repeatedly: existing rows are left as they are.
"""

import argparse
import getpass
import json
from pathlib import Path

from sqlalchemy import select

from app.database.init_db import create_tables
from app.database.session import SessionLocal
from app.models import DataSource, Insurer, Service, User
from app.services.auth_service import hash_password

DATA_FILE = Path(__file__).with_name("reference_data.json")

DATA_SOURCES = [
    ("google_places", "Google Places", "Facility listings discovered with Google Places API (New).", "Listing details from Google Maps"),
    ("reprocare_bot", "ReproCare data bot", "Records submitted by the ReproCare collection bot.", "Collected by the ReproCare data bot"),
]


def load_reference(db) -> dict:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    created = {"services": 0, "insurers": 0, "data_sources": 0}

    for s in data["services"]:
        if not db.scalar(select(Service.id).where(Service.slug == s["slug"])):
            db.add(Service(**s))
            created["services"] += 1
    for i in data["insurers"]:
        if not db.scalar(select(Insurer.id).where(Insurer.slug == i["slug"])):
            db.add(Insurer(**i))
            created["insurers"] += 1
    # Health-library articles are loaded by the content workstream's own seed.
    for code, name, description, attribution in DATA_SOURCES:
        if not db.scalar(select(DataSource.id).where(DataSource.code == code)):
            db.add(DataSource(code=code, name=name, description=description, attribution=attribution))
            created["data_sources"] += 1
    db.commit()
    return created


def create_admin(db, email: str, name: str, password: str) -> str:
    email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        return "exists"
    if len(password) < 10:
        raise SystemExit("Use an administrator password of at least 10 characters.")
    db.add(User(email=email, full_name=name.strip(), password_hash=hash_password(password), role="admin"))
    db.commit()
    return "created"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--admin-email")
    parser.add_argument("--admin-name", default="ReproCare Administrator")
    args = parser.parse_args()

    create_tables()
    with SessionLocal() as db:
        print("Reference data added:", load_reference(db))
        if args.admin_email:
            password = getpass.getpass("New administrator password: ")
            print("Administrator", args.admin_email, create_admin(db, args.admin_email, args.admin_name, password))


if __name__ == "__main__":
    main()
