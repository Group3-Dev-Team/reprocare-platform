"""Cache and daily cap for Google Places requests (from the legacy scripts' places_cache.py, generalised).

A private SQLite file keeps each response for CACHE_DAYS and counts billed requests per day, so repeated
bot runs do not repeat charges. Raise the cap deliberately with REPROCARE_PLACES_DAILY_LIMIT.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from bot_config import CACHE_DIR, private_dir

DATABASE = CACHE_DIR / "places.sqlite3"
DAILY_LIMIT = int(os.environ.get("REPROCARE_PLACES_DAILY_LIMIT", "100"))
CACHE_DAYS = 30


class DailyLimitReached(RuntimeError):
    pass


def _connect():
    private_dir(CACHE_DIR)
    db = sqlite3.connect(DATABASE, isolation_level=None)
    try:
        os.chmod(DATABASE, 0o600)
    except OSError:  # pragma: no cover
        pass
    db.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, body TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, requests INTEGER NOT NULL)")
    return db


def requests_today() -> int:
    with _connect() as db:
        row = db.execute("SELECT requests FROM usage WHERE day = ?", (datetime.now(timezone.utc).date().isoformat(),)).fetchone()
        return row[0] if row else 0


def cached_request(key: str, fetch, refresh: bool = False):
    now = datetime.now(timezone.utc)
    db = _connect()
    try:
        if not refresh:
            row = db.execute("SELECT body, updated_at FROM responses WHERE key = ?", (key,)).fetchone()
            if row and now - datetime.fromisoformat(row[1]) < timedelta(days=CACHE_DAYS):
                return json.loads(row[0])

        today = now.date().isoformat()
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT requests FROM usage WHERE day = ?", (today,)).fetchone()
        if (row[0] if row else 0) >= DAILY_LIMIT:
            db.execute("ROLLBACK")
            raise DailyLimitReached(f"Google Places daily request limit ({DAILY_LIMIT}) reached")
        db.execute("INSERT INTO usage (day, requests) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET requests = requests + 1", (today,))
        db.execute("COMMIT")

        body = fetch()
        db.execute("INSERT OR REPLACE INTO responses (key, body, updated_at) VALUES (?, ?, ?)", (key, json.dumps(body), now.isoformat()))
        return body
    finally:
        db.close()
