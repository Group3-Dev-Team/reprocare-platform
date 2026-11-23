"""Application settings, read once from environment variables (or backend/.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://reprocare:reprocare@localhost:5432/reprocare")
    environment: str = os.getenv("APP_ENV", "development")  # development | test | production

    # Comma-separated list of browser origins allowed to call the API.
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    # How long a sign-in session lasts.
    session_days: int = int(os.getenv("SESSION_DAYS", "14"))

    # Shared secret the external data bot sends in the X-Import-Key header. Empty = bot imports disabled.
    import_api_key: str = os.getenv("IMPORT_API_KEY", "")

    # Google Places API (New). Server-side key only; never expose it to the browser.
    google_places_api_key: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

    google_oauth_enabled: bool = _bool("GOOGLE_OAUTH_ENABLED")
    google_oauth_client_id: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    google_oauth_client_secret: str = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    google_oauth_redirect_uri: str = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()

    local_facebook_demo: bool = _bool("LOCAL_FACEBOOK_DEMO")

    # Demo accounts (patient@reprocare.demo etc.) are refused in production.
    allow_demo_accounts: bool = _bool("ALLOW_DEMO_ACCOUNTS", True)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
