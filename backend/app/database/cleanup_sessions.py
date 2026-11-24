"""Delete expired sign-in sessions. Active sessions and all other data are left unchanged.

Run from backend/ (for example daily from a scheduler):
    python -m app.database.cleanup_sessions            delete expired sessions
    python -m app.database.cleanup_sessions --dry-run  only count them
"""

import argparse

from sqlalchemy.exc import SQLAlchemyError

from app.database.session import SessionLocal
from app.services.auth_service import purge_expired_sessions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="count expired sessions without deleting them")
    args = parser.parse_args(argv)
    try:
        with SessionLocal() as db:
            count = purge_expired_sessions(db, dry_run=args.dry_run)
    except SQLAlchemyError:
        raise SystemExit("Session cleanup could not reach the database.") from None
    if args.dry_run:
        print(f"{count} expired session{'s' if count != 1 else ''} would be deleted (dry run, nothing changed).")
    else:
        print(f"Deleted {count} expired session{'s' if count != 1 else ''}.")


if __name__ == "__main__":
    main()
