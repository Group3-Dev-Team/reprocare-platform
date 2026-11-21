"""Private staging files between collection and import.

New collections: one normalised batch per post at  BATCHES/<platform>/<facility-slug>__<post-id>.json
Collections staged by the legacy scripts are read too, so previously collected data can be imported:
  * feedback/<hospital>_<hash>.json           Facebook comment candidates (facility NAME, no slug)
  * staging/tiktok_auto/<video-id>.json       {"facility", "video_url", "records": [...]}
  * staging/google_maps_reviews.json          Apify Google Maps reviews (placeId per review)
Legacy batches carry `facility_name` instead of a slug; the importer resolves it only on an exact,
unique name match (see importer.resolve_name).
"""

import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from bot_config import BATCHES, LEGACY_FACEBOOK_DIR, LEGACY_GOOGLE_FILE, LEGACY_TIKTOK_DIR, private_dir


def facebook_post_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def write_batch(batch: dict) -> Path:
    folder = private_dir(BATCHES / batch["platform"])
    key = re.sub(r"[^A-Za-z0-9_-]+", "_", batch["post"]["external_id"])[:60]
    path = folder / f"{batch.get('facility_slug') or 'unlinked'}__{key}.json"
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def read_batches() -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(BATCHES.glob("*/*.json")) if BATCHES.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("  unreadable batch skipped:", path.name)
            continue
        if isinstance(data, dict) and data.get("platform") and isinstance(data.get("post"), dict):
            out.append((path, data))
    return out


# --------------------------------------------------------------------------- legacy staging formats

def legacy_facebook() -> list[dict]:
    """The legacy scripts: list of {facility, platform, text, source_url, collected_at} per file. Validated as in feedback_pipeline.py."""
    if not LEGACY_FACEBOOK_DIR.is_dir():
        return []
    posts = defaultdict(lambda: {"comments": {}, "facility": None, "collected_at": None})
    pattern = re.compile(r"^[a-z0-9_]+_[0-9a-f]{12}\.json$")
    for path in sorted(LEGACY_FACEBOOK_DIR.glob("*.json")):
        if not pattern.fullmatch(path.name):
            continue
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in records if isinstance(records, list) else []:
            if not isinstance(r, dict) or r.get("platform") != "facebook":
                continue
            url, text, facility = r.get("source_url"), r.get("text"), r.get("facility")
            if not all(isinstance(v, str) and v.strip() for v in (url, text, facility)):
                continue
            parsed = urlparse(url)
            if parsed.scheme != "https" or "/posts/" not in parsed.path:
                continue
            ident = hashlib.sha256((url + "\n" + text.strip()).encode("utf-8")).hexdigest()
            entry = posts[url]
            entry["facility"] = facility.strip()
            entry["collected_at"] = r.get("collected_at")
            entry["comments"][ident] = {"external_id": ident, "text": text, "collected_at": r.get("collected_at")}
    return [
        {
            "platform": "facebook",
            "facility_name": e["facility"],
            "post": {"external_id": facebook_post_id(url), "url": url, "collected_at": e["collected_at"], "match_method": "facility_page_post"},
            "comments": list(e["comments"].values()),
        }
        for url, e in posts.items()
    ]


def legacy_tiktok() -> list[dict]:
    from tiktok_collector import VIDEO_URL, comments_from_dataset

    out = []
    for path in sorted(LEGACY_TIKTOK_DIR.glob("*.json")) if LEGACY_TIKTOK_DIR.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            continue
        url = data.get("video_url") or ""
        match = VIDEO_URL.search(url)
        if not match or not data.get("facility"):
            continue
        out.append(
            {
                "platform": "tiktok",
                "facility_name": data["facility"],
                "post": {"external_id": match.group(1), "url": match.group(0), "match_method": "caption_exact_name"},
                "comments": comments_from_dataset(data["records"], match.group(1)),
            }
        )
    return out


def legacy_google() -> list[dict]:
    """The legacy scripts' Apify Google Maps reviews export, grouped by placeId (an exact identifier)."""
    if not LEGACY_GOOGLE_FILE.is_file():
        return []
    try:
        records = json.loads(LEGACY_GOOGLE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    by_place = defaultdict(list)
    for item in records if isinstance(records, list) else []:
        if not isinstance(item, dict) or not item.get("placeId") or not item.get("reviewId"):
            continue
        by_place[item["placeId"]].append(item)
    out = []
    for place_id, items in by_place.items():
        url = items[0].get("url") or f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        comments = []
        for i in items:
            try:
                stars = int(float(i.get("stars")))
            except (TypeError, ValueError):
                stars = None
            comments.append(
                {
                    "external_id": str(i["reviewId"]),
                    "author_name": i.get("name") or i.get("reviewerName") or "",
                    "text": i.get("text") or i.get("reviewText") or "",
                    "published_at": i.get("publishedAtDate"),
                    "source_rating": stars if stars in (1, 2, 3, 4, 5) else None,
                }
            )
        out.append(
            {
                "platform": "google",
                "google_place_id": place_id,
                "post": {"external_id": place_id, "url": url, "caption": "Reviews shown on Google Maps", "match_method": "google_place_id"},
                "comments": comments,
            }
        )
    return out


def legacy_batches() -> list[dict]:
    return legacy_facebook() + legacy_tiktok() + legacy_google()
