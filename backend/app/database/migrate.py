"""Apply additive, versioned migrations. Never drops a table or deletes data.

    python -m app.database.migrate            # apply anything not yet applied
    python -m app.database.migrate --status   # list applied / pending

Step 1 creates any table that does not exist yet (SQLAlchemy create_all only ADDS missing tables).
Step 2 runs each file in backend/migrations/versions/ once, in name order, inside a transaction, and
records it in `schema_migrations`. Files are `.sql` (run as-is) or `.py` (must define `upgrade(db)`).
"""

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import text

import app.models  # noqa: F401  (registers every table)
from app.database.session import Base, SessionLocal, engine

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def _applied(db) -> set[str]:
    db.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(120) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
    db.commit()
    return set(db.scalars(text("SELECT version FROM schema_migrations")))


def pending(db) -> list[Path]:
    done = _applied(db)
    files = sorted(p for p in VERSIONS.glob("*") if p.suffix in {".sql", ".py"} and not p.name.startswith("_"))
    return [p for p in files if p.stem not in done]


def run_file(db, path: Path) -> None:
    if path.suffix == ".sql":
        db.execute(text(path.read_text(encoding="utf-8")))
    else:
        spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.upgrade(db)
    db.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": path.stem})


def lock_down_supabase_data_api(db) -> int:
    """On Supabase only: enable Row Level Security (no policies) on every ReproCare table.

    Supabase publishes tables in `public` through its Data API to the `anon`/`authenticated` roles. ReproCare does
    not use that API (all access goes through the FastAPI backend, which connects as the table owner and is not
    affected), so RLS without policies simply closes it. Local PostgreSQL has no `anon` role: nothing happens.
    """
    if not db.scalar(text("SELECT count(*) = 2 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")):
        return 0
    names = [t.name for t in Base.metadata.sorted_tables] + ["schema_migrations"]
    changed = 0
    for name in names:
        enabled = db.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:t)"), {"t": f"public.{name}"})
        if enabled is False:
            db.execute(text(f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY'))
            changed += 1
    db.commit()
    return changed


def migrate(verbose: bool = True) -> list[str]:
    Base.metadata.create_all(engine)
    applied = []
    with SessionLocal() as db:
        for path in pending(db):
            try:
                run_file(db, path)
                db.commit()
            except Exception:
                db.rollback()
                raise
            applied.append(path.stem)
            if verbose:
                print("Applied", path.stem)
        locked = lock_down_supabase_data_api(db)
        if verbose and locked:
            print(f"Supabase: Row Level Security enabled on {locked} tables (closes the public Data API; the backend is unaffected)")
    if verbose and not applied:
        print("Database is up to date.")
    return applied


if __name__ == "__main__":
    if "--status" in sys.argv:
        Base.metadata.create_all(engine)
        with SessionLocal() as session:
            todo = {p.stem for p in pending(session)}
            for p in sorted(VERSIONS.glob("*")):
                if p.suffix in {".sql", ".py"}:
                    print(("pending " if p.stem in todo else "applied ") + p.stem)
    else:
        migrate()
