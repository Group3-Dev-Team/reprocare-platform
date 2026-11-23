"""Guard used by test fixtures that drop and recreate tables.

Destructive test setup must only ever run against a dedicated disposable database.
The guard refuses a target whose database name does not identify it as a test or
scratch database, or which matches the application database configured in backend/.env.
"""

from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_MARKERS = ("test", "scratch")


def _identity(url: str) -> tuple[str, int, str]:
    parsed = make_url(url)
    host = (parsed.host or "localhost").lower()
    if host in {"127.0.0.1", "::1"}:
        host = "localhost"
    return host, parsed.port or 5432, (parsed.database or "").lower()


def assert_disposable_database(url: str) -> None:
    """Raise RuntimeError unless ``url`` names a disposable test or scratch database."""
    _, _, name = _identity(url)
    if not any(marker in name for marker in _MARKERS):
        raise RuntimeError(
            f"Refusing to reset database '{name}': test databases must contain 'test' or 'scratch' in their name."
        )
    configured = dotenv_values(_ENV_FILE).get("DATABASE_URL") if _ENV_FILE.exists() else None
    if configured and _identity(configured) == _identity(url):
        raise RuntimeError("Refusing to reset the application database configured in backend/.env.")
