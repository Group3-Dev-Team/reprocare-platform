"""Shared configuration for the ReproCare bot. Reads backend/.env (relative to this repository) and the
process environment. Secrets are read here and never printed."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ENV_FILE = BACKEND / ".env"

# Make the backend package importable so the bot writes through the same models and rules as the API.
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:  # python-dotenv is a backend dependency
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
except ImportError:  # pragma: no cover
    pass

# Where collected raw data, the Facebook browser profile and the Places cache live.
# Defaults to the same folder the legacy scripts used, so existing collections and the signed-in Facebook profile keep working.
DATA_HOME = Path(os.environ.get("REPROCARE_BOT_HOME", Path.home() / ".local/share/reprocare-browser")).expanduser()
if DATA_HOME.resolve().is_relative_to(ROOT.resolve()):
    # The folder holds the signed-in Facebook session; keeping it out of the project keeps it out of git and ZIPs.
    print("Warning: REPROCARE_BOT_HOME is inside the project folder; move it outside so browser sessions cannot be committed or zipped.", file=sys.stderr)
FACEBOOK_PROFILE = DATA_HOME / "facebook"
STAGING = DATA_HOME / "staging"
BATCHES = STAGING / "batches"  # normalised batches written by this bot, one JSON per post
LEGACY_FACEBOOK_DIR = DATA_HOME / "feedback"  # the legacy scripts' per-post Facebook files
LEGACY_TIKTOK_DIR = STAGING / "tiktok_auto"  # the legacy scripts' per-video TikTok files
LEGACY_GOOGLE_FILE = STAGING / "google_maps_reviews.json"  # the legacy scripts' Apify Google Maps export
CACHE_DIR = DATA_HOME / "cache"

# Optional: use an installed Chrome/Chromium instead of Playwright's bundled browser.
BROWSER_PATH = os.environ.get("REPROCARE_BOT_BROWSER_PATH", "").strip()


def launch_kwargs(headless: bool | None = None) -> dict:
    kwargs = {"headless": HEADLESS if headless is None else headless}
    if BROWSER_PATH:
        kwargs["executable_path"] = BROWSER_PATH
    return kwargs


HEADLESS = os.environ.get("REPROCARE_BOT_HEADLESS", "true").strip().lower() not in {"0", "false", "no"}


def secret(*names: str) -> str | None:
    for name in names:
        value = (os.environ.get(name) or "").strip().strip('"').strip("'")
        if value:
            return value
    return None


def google_api_key() -> str | None:
    return secret("GOOGLE_PLACES_API_KEY")


def apify_token() -> str | None:
    return secret("APIFY_API_TOKEN", "APIFY_TOKEN", "APIFY_API_KEY")


def import_key() -> str | None:
    return secret("IMPORT_API_KEY")


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:  # pragma: no cover (e.g. Windows)
        pass
    return path
