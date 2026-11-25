"""Safe configuration check: which settings are present, what each enables, and whether the database answers.

    python -m app.check_config            (from backend/)

Never prints a secret: values are reported only as "set" / "missing", database URLs with the password removed.
Exit code 1 when something required for the selected use is missing or the database cannot be reached.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
ENV_FILE = BACKEND / ".env"

# (name, required, what it is for)
VARIABLES = [
    ("DATABASE_URL", True, "Database connection — local PostgreSQL or Supabase PostgreSQL"),
    ("APP_ENV", False, "development | test | production (defaults to development)"),
    ("CORS_ORIGINS", False, "Browser origins allowed to call the API (defaults to http://localhost:5173)"),
    ("SESSION_DAYS", False, "Sign-in length in days (defaults to 14)"),
    ("GOOGLE_PLACES_API_KEY", False, "Google Places: facility discovery, Google rating/reviews, live search page"),
    ("APIFY_API_TOKEN", False, "Apify: TikTok video and comment collection (billable)"),
    ("IMPORT_API_KEY", False, "Only for a bot importing over HTTP (`import --api`); direct imports do not need it"),
    ("TEST_DATABASE_URL", False, "pytest only — a database the test run may reset"),
]
BOT_VARIABLES = [
    ("REPROCARE_BOT_HOME", "Bot data folder (defaults to ~/.local/share/reprocare-browser)"),
    ("REPROCARE_BOT_BROWSER_PATH", "Use an installed Chrome for Playwright (optional)"),
]


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "?"
    user = parts.username or ""
    if ".supabase." in host:
        user = user.split(".")[0] + (".****" if "." in user else "")
        host = ".".join("****" if i == 1 and host.startswith("db.") else p for i, p in enumerate(host.split(".")))
    return f"{parts.scheme}://{user + ':***@' if user else ''}{host}{':' + str(parts.port) if parts.port else ''}{parts.path}"


def describe_database(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host.endswith((".supabase.co", ".supabase.com")):
        if "pooler" in host:
            return "Supabase — transaction pooler (prepared statements disabled)" if parts.port == 6543 else "Supabase — session pooler"
        return "Supabase — direct connection"
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "Local PostgreSQL on this computer"
    return "PostgreSQL server"


def main() -> int:
    from dotenv import load_dotenv

    print("ReproCare configuration check (values are never shown)\n")
    print(f"backend/.env:          {'found' if ENV_FILE.is_file() else 'NOT FOUND — copy backend/.env.example to backend/.env'}")
    print(f"frontend/.env.local:   {'found' if (ROOT / 'frontend' / '.env.local').is_file() else 'not found (optional; defaults to http://localhost:8000)'}")
    load_dotenv(ENV_FILE)

    problems = []
    print("\nVariables")
    for name, required, purpose in VARIABLES:
        present = bool((os.environ.get(name) or "").strip())
        state = "set" if present else ("MISSING" if required else "not set")
        print(f"  {name:<27} {state:<8} {purpose}")
        if required and not present:
            problems.append(f"{name} is required")
    for name, purpose in BOT_VARIABLES:
        print(f"  {name:<27} {'set' if (os.environ.get(name) or '').strip() else 'not set':<8} {purpose}")

    from app.config import settings
    from app.database.session import DATABASE_URL, engine

    print("\nDatabase")
    print(f"  Type:      {describe_database(DATABASE_URL)}")
    print(f"  Address:   {safe_url(DATABASE_URL)}")
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            version = conn.scalar(text("SHOW server_version"))
            name = conn.scalar(text("SELECT current_database()"))
            tables = conn.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            print(f"  Connected: yes (PostgreSQL {version}, database '{name}', {tables} tables)")
            if not tables:
                print("  Next step: python -m app.database.migrate")
            if conn.scalar(text("SELECT count(*) = 2 FROM pg_roles WHERE rolname IN ('anon','authenticated')")):
                open_tables = conn.scalar(text(
                    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity"))
                print(f"  Supabase Data API: {'closed (RLS on all tables)' if not open_tables else f'{open_tables} tables exposed — run python -m app.database.migrate'}")
    except Exception as exc:  # connection errors never contain the password with psycopg 3
        print(f"  Connected: NO ({type(exc).__name__}: {str(exc).splitlines()[0][:160]})")
        problems.append("database unreachable")

    if (os.environ.get("REPROCARE_REQUIRE_SHARED_DATABASE") or "").strip().lower() in {"1", "true", "yes", "on"}:
        from app.database.session import require_shared_database
        try:
            print(f"  Shared database required: yes, connected as {require_shared_database()}")
        except Exception as exc:  # the guard's messages never contain the address or password
            print(f"  Shared database required: FAILED ({str(exc).splitlines()[0][:160]})")
            problems.append("not connected to the shared database")

    print("\nIntegrations")
    print(f"  Google Places:  {'ready' if settings.google_places_api_key else 'unavailable — set GOOGLE_PLACES_API_KEY'}")
    print(f"  Apify (TikTok): {'ready' if (os.environ.get('APIFY_API_TOKEN') or '').strip() else 'unavailable — set APIFY_API_TOKEN'}")
    home = Path(os.environ.get("REPROCARE_BOT_HOME") or Path.home() / ".local/share/reprocare-browser").expanduser()
    profile = home / "facebook"
    print(f"  Facebook:       {'signed-in browser profile found' if profile.is_dir() and any(profile.iterdir()) else 'no browser profile yet — run: python browser_bot/reprocare_bot.py facebook-login'}")
    print(f"  Environment:    {settings.environment}{' (sample @reprocare.demo accounts refused)' if settings.is_production or not settings.allow_demo_accounts else ''}")

    print("\nResult:", "OK" if not problems else "needs attention — " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
