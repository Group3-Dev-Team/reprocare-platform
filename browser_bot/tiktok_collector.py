"""TikTok video discovery and comment collection through Apify (the legacy scripts' tiktok_auto.py, preserved).

Actors (unchanged from the legacy scripts):
  search   : epctex~tiktok-search-scraper
  comments : socialdataapi~tiktok-comments-scraper
Bounds (unchanged): ≤10 search results per term, ≤2 videos per facility, ≤10 top-level comments per video,
≤2 replies per comment. Apify bills per run; live runs require --allow-paid-apify.

Facility association: the bot runs for ONE facility and keeps a video only when its caption contains the
facility's full name (the legacy scripts' `relevant()` rule). Short aliases are not used unless configured explicitly.
"""

import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot_config import apify_token

SEARCH_ACTOR = "epctex~tiktok-search-scraper"
COMMENTS_ACTOR = "socialdataapi~tiktok-comments-scraper"
VIDEO_URL = re.compile(r"https://(?:www\.)?tiktok\.com/@[\w.-]+/video/(\d+)")


class ApifyUnavailable(RuntimeError):
    pass


APIFY_BASE = "https://api.apify.com/v2"
# the legacy scripts' endpoint first (unchanged), then Apify's documented Actor endpoint — only after an HTTP 404.
ENDPOINT_PREFIXES = ("actors", "acts")
HTTP_REASONS = {
    401: "token rejected — check APIFY_API_TOKEN",
    403: "token lacks permission for this Actor, or the account is restricted",
    429: "rate limit reached — wait and try again",
}


def actor_endpoint(prefix: str, actor: str) -> str:
    # Same path, query and synchronous run as the legacy scripts: run-sync-get-dataset-items with a 120 s Actor timeout.
    return f"{APIFY_BASE}/{prefix}/{actor}/run-sync-get-dataset-items?timeout=120"


def actor_run(actor: str, payload: dict) -> list:
    token = apify_token()
    if not token:
        raise ApifyUnavailable("APIFY_API_TOKEN is not set in backend/.env")
    body = json.dumps(payload).encode("utf-8")
    for prefix in ENDPOINT_PREFIXES:
        endpoint = actor_endpoint(prefix, actor)
        print(f"  Apify: POST {endpoint.split('?')[0]}", flush=True)  # the token travels in a header and is never logged
        request = Request(endpoint, data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=135) as response:  # the legacy scripts' client timeout
                data = json.load(response)
            break
        except HTTPError as exc:
            if exc.code == 404 and prefix != ENDPOINT_PREFIXES[-1]:
                print(f"  Apify: HTTP 404 on /v2/{prefix}/… — retrying with the documented /v2/{ENDPOINT_PREFIXES[-1]}/… endpoint", flush=True)
                continue
            reason = HTTP_REASONS.get(exc.code) or ("Apify server error — try again later" if exc.code >= 500 else "request refused")
            raise ApifyUnavailable(f"Apify HTTP {exc.code} for {actor}: {reason}") from None
        except (URLError, TimeoutError) as exc:
            raise ApifyUnavailable(f"Could not reach Apify ({type(exc).__name__})") from None
    if not isinstance(data, list):  # the legacy scripts' result check
        raise ApifyUnavailable("Unexpected Apify result format")
    print(f"  Apify: {len(data)} items from /v2/{prefix}/…", flush=True)
    return data


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").casefold()).split())


def video_url(record: dict) -> str | None:
    if not isinstance(record, dict):
        return None
    for key in ("url", "videoWebUrl", "webVideoUrl", "shareUrl"):
        value = record.get(key)
        if isinstance(value, str):
            match = VIDEO_URL.search(value)
            if match:
                return match.group(0)
    return None


def caption(record: dict) -> str:
    return str(record.get("desc") or record.get("description") or record.get("text") or record.get("title") or "")


def relevant(record: dict, facility_name: str, aliases=()) -> bool:
    """Full facility name in the caption (legacy scripts). Aliases must appear together with the facility's town."""
    text = _norm(caption(record))
    if _norm(facility_name) and _norm(facility_name) in f" {text} ":
        return True
    return any(re.search(rf"\b{re.escape(_norm(a))}\b", text) and town in text for a, town in aliases)


def _first(record: dict, *paths):
    for path in paths:
        value = record
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
            if value is None:
                break
        if isinstance(value, list):
            value = value[0] if value else None
        if value not in (None, ""):
            return value
    return None


def _iso(value) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, (int, float)) and value > 1_000_000_000:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    return None


def video_context(record: dict, url: str) -> dict:
    author = _first(record, "author.uniqueId", "authorMeta.name", "author.nickname", "authorMeta.nickName", "author")
    thumb = _first(record, "video.cover", "videoMeta.coverUrl", "covers", "video.originCover", "cover")
    return {
        "external_id": VIDEO_URL.search(url).group(1),
        "url": url,
        "author_name": ("@" + str(author)) if author and isinstance(author, str) and not str(author).startswith("@") else (author or ""),
        "caption": caption(record)[:10000],
        "thumbnail_url": thumb if isinstance(thumb, str) and thumb.startswith("https://") else "",
        "published_at": _iso(_first(record, "createTimeISO", "createTime")),
        "match_method": "caption_exact_name",
    }


def comments_from_dataset(records: list, video_id: str) -> list[dict]:
    """Normalise the comments actor output (top-level comments with nested `replies`)."""
    out, seen = [], set()

    def add(entry, parent):
        if not isinstance(entry, dict):
            return
        cid = str(entry.get("cid") or entry.get("id") or "")
        text = entry.get("text")
        url = entry.get("videoWebUrl") or ""
        if not cid.isdecimal() or not isinstance(text, str) or not text.strip() or cid in seen:
            return
        if url and video_id not in url:
            return  # belongs to another video
        seen.add(cid)
        author = _first(entry, "uniqueId", "user.uniqueId", "user.unique_id", "author.uniqueId", "nickname", "user.nickname")
        likes = entry.get("diggCount") if isinstance(entry.get("diggCount"), int) else None
        out.append(
            {
                "external_id": cid,
                "parent_external_id": parent,
                "author_name": ("@" + author) if isinstance(author, str) and author and not author.startswith("@") else "",
                "text": text,
                "published_at": _iso(entry.get("createTimeISO") or entry.get("createTime")),
                "like_count": likes,
            }
        )
        for reply in entry.get("replies") or []:
            add(reply, cid)

    for record in records:
        add(record, None)
    return out


def collect_for_facility(facility_name: str, town: str = "", max_videos: int | None = None, comments_per_video: int = 500) -> list[dict]:
    """Two-step Apify collection. Returns raw bundles: [{'search_record', 'url', 'comments_raw'}]."""
    terms = [facility_name, f"{facility_name} {town}".strip()] if town and town.casefold() not in facility_name.casefold() else [facility_name]
    candidates: dict[str, dict] = {}
    for term in terms:
        for record in actor_run(SEARCH_ACTOR, {"search": [term], "maxItems": 500, "endPage": 10, "sortType": "RELEVANCE"}):
            url = video_url(record)
            if url and relevant(record, facility_name):
                candidates.setdefault(url, record)
    bundles = []
    for url, record in list(candidates.items())[:max_videos] if max_videos is not None else list(candidates.items()):
        raw = actor_run(COMMENTS_ACTOR, {"postURLs": [url], "commentsPerPost": comments_per_video, "maxRepliesPerComment": 100})
        bundles.append({"search_record": record, "url": url, "comments_raw": raw})
    return bundles


def bundle_to_batch(bundle: dict, facility_slug: str) -> dict:
    url = bundle["url"]
    post = video_context(bundle.get("search_record") or {}, url)
    post["collected_at"] = bundle.get("collected_at") or datetime.now(timezone.utc).isoformat()
    return {"platform": "tiktok", "facility_slug": facility_slug, "post": post, "comments": comments_from_dataset(bundle.get("comments_raw") or [], post["external_id"])}
