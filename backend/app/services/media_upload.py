"""Signed direct uploads of facility photos to Cloudinary.

The browser never receives the API secret. The backend checks the caller's role and facility, validates the file
type and size it declares, and returns short-lived signed parameters for one upload into that facility's folder.
Cloudinary enforces the signed folder, public id, formats and size limit.

Publishing an uploaded photo on a listing additionally needs a stored photo field and an approved review step; until
then the dashboard keeps the in-browser preview. See docs/DEPLOYMENT.md for the configuration.
"""

import hashlib
import os
import secrets
import time

ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_BYTES = 5 * 1024 * 1024


def _config() -> dict:
    return {
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME", "").strip(),
        "api_key": os.getenv("CLOUDINARY_API_KEY", "").strip(),
        "api_secret": os.getenv("CLOUDINARY_API_SECRET", "").strip(),
        "folder": os.getenv("CLOUDINARY_UPLOAD_FOLDER", "reprocare/facilities").strip().strip("/"),
    }


def enabled() -> bool:
    cfg = _config()
    return bool(cfg["cloud_name"] and cfg["api_key"] and cfg["api_secret"])


def sign(params: dict, api_secret: str) -> str:
    """Cloudinary signature: SHA-1 of the alphabetically sorted `key=value` pairs joined by `&`, then the secret."""
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params) if params[key] not in (None, ""))
    return hashlib.sha1((payload + api_secret).encode("utf-8")).hexdigest()


def upload_parameters(facility_slug: str, content_type: str, size: int) -> dict:
    if content_type not in ALLOWED_TYPES:
        raise ValueError("Choose a JPEG, PNG or WebP image.")
    if size <= 0 or size > MAX_BYTES:
        raise ValueError("Choose an image smaller than 5 MB.")
    cfg = _config()
    params = {
        "allowed_formats": ",".join(sorted(set(ALLOWED_TYPES.values()))),
        "folder": f"{cfg['folder']}/{facility_slug}",
        "public_id": secrets.token_hex(12),
        "timestamp": int(time.time()),
    }
    return {
        **params,
        "api_key": cfg["api_key"],
        "signature": sign(params, cfg["api_secret"]),
        "upload_url": f"https://api.cloudinary.com/v1_1/{cfg['cloud_name']}/image/upload",
        "max_bytes": MAX_BYTES,
    }
