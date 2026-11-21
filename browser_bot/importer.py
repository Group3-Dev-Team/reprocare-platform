"""Import staged batches into ReproCare — directly into the database (default), or over HTTP to a running
API with the X-Import-Key header (`--api http://host:8000`). Both paths use the same validation:
app.services.external_feedback_service.import_batches.
"""

import json
import urllib.error
import urllib.request

import bot_config  # noqa: F401
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import Facility
from app.schemas.external import ExternalBatchIn
from app.services.external_feedback_service import import_batches, record_run


def resolve_name(db, name: str) -> str | None:
    """Exact (case/whitespace-insensitive) name that matches exactly ONE facility. No partial or fuzzy matching."""
    norm = " ".join((name or "").split()).casefold()
    if not norm:
        return None
    matches = db.scalars(select(Facility.slug).where(func.lower(func.regexp_replace(func.trim(Facility.name), r"\s+", " ", "g")) == norm)).all()
    return matches[0] if len(matches) == 1 else None


def _prepare(db, raw: list[dict]) -> tuple[list[ExternalBatchIn], list[str]]:
    ready, problems = [], []
    for item in raw:
        item = dict(item)
        name = item.pop("facility_name", None)
        if not item.get("facility_slug") and not item.get("google_place_id"):
            slug = resolve_name(db, name)
            if not slug:
                problems.append(f"{item['platform']} post {item['post'].get('url', '')[:80]}: facility '{name}' not found exactly once — not imported")
                continue
            item["facility_slug"] = slug
        try:
            ready.append(ExternalBatchIn.model_validate(item))
        except Exception as exc:  # pydantic ValidationError
            problems.append(f"{item['platform']} post {item['post'].get('external_id')}: invalid ({str(exc).splitlines()[0]})")
    return ready, problems


def import_direct(raw: list[dict], label: str = "import") -> dict:
    with SessionLocal() as db:
        batches, problems = _prepare(db, raw)
        result = import_batches(db, batches) if batches else {"received": 0, "imported": 0, "comments_created": 0, "comments_skipped": 0, "errors": [], "results": []}
        result["unresolved"] = problems
        record_run(
            db,
            "import",
            "succeeded" if not (result["errors"] or problems) else "failed" if not result["imported"] else "succeeded",
            f"{label}: {result['imported']} posts, {result['comments_created']} new comments, {len(result['errors']) + len(problems)} problems",
            posts_found=result["imported"],
            comments_created=result["comments_created"],
            comments_skipped=result["comments_skipped"],
        )
        db.commit()
    return result


def import_http(raw: list[dict], api: str) -> dict:
    """For a bot running on another machine. Facility names must already be resolved to slugs."""
    key = bot_config.import_key()
    if not key:
        raise SystemExit("IMPORT_API_KEY is not set; it is required for --api imports")
    unresolved = [b for b in raw if not b.get("facility_slug") and not b.get("google_place_id")]
    raw = [b for b in raw if b not in unresolved]
    totals = {"received": 0, "imported": 0, "comments_created": 0, "comments_skipped": 0, "errors": [], "unresolved": [f"{len(unresolved)} legacy batches need a direct import"] if unresolved else []}
    for start in range(0, len(raw), 50):
        body = json.dumps({"batches": raw[start : start + 50]}, default=str).encode("utf-8")
        request = urllib.request.Request(api.rstrip("/") + "/api/import/external-feedback", data=body, method="POST", headers={"Content-Type": "application/json", "X-Import-Key": key})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                part = json.load(response)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"Import API returned HTTP {exc.code}") from None
        for k in ("received", "imported", "comments_created", "comments_skipped"):
            totals[k] += part.get(k, 0)
        totals["errors"] += part.get("errors", [])
    return totals
