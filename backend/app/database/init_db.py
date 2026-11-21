"""Create (or reset) the database tables from the SQLAlchemy models.

    python -m app.database.init_db           # create any missing tables
    python -m app.database.init_db --reset   # DROP everything and recreate (development only)

The same table definitions are exported to database/schema.sql by `python -m app.database.export_schema`.
"""

import sys

from app.config import settings
from app.database.session import Base, engine
import app.models  # noqa: F401  (registers every table on Base.metadata)


def create_tables(reset: bool = False) -> None:
    if reset:
        if settings.is_production:
            raise SystemExit("Refusing to drop tables in production.")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    create_tables(reset=reset)
    print(("Recreated" if reset else "Created") + f" {len(Base.metadata.tables)} tables.")
