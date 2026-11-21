"""Database engine, session factory and the declarative Base every model inherits from.

The same code runs against local PostgreSQL (development) and Supabase-hosted PostgreSQL (shared/deployed):
only DATABASE_URL changes. Supabase connection strings can be pasted as Supabase shows them:

* `postgresql://…` / `postgres://…` is converted to the psycopg 3 driver (`postgresql+psycopg://…`);
* Supabase hosts (*.supabase.co, *.supabase.com) get `sslmode=require` unless the URL already sets sslmode;
* Supabase's transaction pooler (port 6543, PgBouncer transaction mode) cannot keep prepared statements,
  so they are switched off for that port. The session pooler (5432) and direct connections need nothing extra.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

SUPABASE_SUFFIXES = (".supabase.co", ".supabase.com")


def is_supabase(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host.endswith(SUPABASE_SUFFIXES)


def normalize_database_url(url: str) -> str:
    """Accept Supabase-style URLs unchanged by the user; never alters credentials."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
            break
    if is_supabase(url):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query.setdefault("sslmode", "require")
        url = urlunsplit(parts._replace(query=urlencode(query)))
    return url


def connect_args_for(url: str) -> dict:
    parts = urlsplit(url)
    if is_supabase(url) and parts.port == 6543:
        return {"prepare_threshold": None}  # PgBouncer transaction mode
    return {}


DATABASE_URL = normalize_database_url(settings.database_url)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args_for(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
