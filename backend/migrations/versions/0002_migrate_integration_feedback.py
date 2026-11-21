"""0002: copy feedback collected by the integration build (table `external_feedback`) into the new tables.

Runs only if `external_feedback` exists (i.e. on the reprocare_integration_dev database). The legacy
table and `external_google_ratings` are LEFT IN PLACE, untouched, so nothing can be lost.

Facility attribution, in order:
  1. the legacy row's facility_id, when it was set;
  2. otherwise a case-insensitive, whitespace-normalised name that equals exactly ONE facility's name
     (the bot ran per named hospital, so this is the name it was collecting for — not a fuzzy match);
  3. otherwise the post is left unlinked (hidden from patients) for an administrator to link.
"""

import hashlib
import re

from sqlalchemy import text

from app.services.feedback_screening import screen_feedback

PLATFORM = {"facebook": "facebook", "tiktok": "tiktok", "google_maps": "google"}


def _norm(name: str) -> str:
    return " ".join((name or "").casefold().split())


def _post_external_id(platform: str, url: str) -> str:
    if platform == "tiktok":
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)
    if platform == "facebook":
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    return "legacy:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def upgrade(db) -> None:
    if not db.scalar(text("SELECT to_regclass('public.external_feedback') IS NOT NULL")):
        print("  no legacy external_feedback table; nothing to migrate")
        return

    facilities = db.execute(text("SELECT id, name FROM facilities")).all()
    by_name: dict[str, list[tuple[int, str]]] = {}
    for fid, name in facilities:
        by_name.setdefault(_norm(name), []).append((fid, name))
    names = {fid: name for fid, name in facilities}

    stars = {}
    place_by_review = {}
    if db.scalar(text("SELECT to_regclass('public.external_google_ratings') IS NOT NULL")):
        for rid, place_id, value in db.execute(text("SELECT review_id, place_id, stars FROM external_google_ratings")):
            stars[rid] = value
            place_by_review[rid] = place_id

    rows = db.execute(
        text(
            "SELECT id, facility_id, facility_name, platform, external_id, source_url, original_text, collected_at "
            "FROM external_feedback ORDER BY id"
        )
    ).mappings().all()

    posts: dict[tuple[str, str], int] = {}
    created_posts = created_comments = skipped = unlinked = 0
    for row in rows:
        platform = PLATFORM.get(row["platform"])
        if not platform or not row["source_url"] or not (row["original_text"] or "").strip():
            skipped += 1
            continue

        facility_id = row["facility_id"]
        if facility_id is None:
            matches = by_name.get(_norm(row["facility_name"]), [])
            facility_id = matches[0][0] if len(matches) == 1 else None

        post_key = (platform, _post_external_id(platform, row["source_url"]))
        post_id = posts.get(post_key)
        if post_id is None:
            post_id = db.scalar(
                text("SELECT id FROM external_posts WHERE platform = :p AND external_id = :e"), {"p": post_key[0], "e": post_key[1]}
            )
            if post_id is None:
                post_id = db.scalar(
                    text(
                        "INSERT INTO external_posts (facility_id, platform, external_id, url, author_name, caption, thumbnail_url, "
                        "collected_at, match_method, is_visible, legacy_facility_name) "
                        "VALUES (:f, :p, :e, :u, '', '', '', :c, 'legacy_import', true, :n) RETURNING id"
                    ),
                    {"f": facility_id, "p": platform, "e": post_key[1], "u": row["source_url"], "c": row["collected_at"], "n": row["facility_name"] or ""},
                )
                created_posts += 1
                if facility_id is None:
                    unlinked += 1
            posts[post_key] = post_id

        if db.scalar(text("SELECT 1 FROM external_comments WHERE platform = :p AND external_id = :e"), {"p": platform, "e": row["external_id"]}):
            skipped += 1
            continue

        result = screen_feedback(names.get(facility_id, row["facility_name"] or ""), row["original_text"])
        # TikTok rows stored the comment's own creation time (createTimeISO) in collected_at.
        published = row["collected_at"] if platform == "tiktok" else None
        db.execute(
            text(
                "INSERT INTO external_comments (post_id, facility_id, parent_id, platform, external_id, author_name, author_is_facility, text, "
                "published_at, published_at_approximate, collected_at, like_count, source_rating, status, screening, screening_reasons) "
                "VALUES (:post, :f, NULL, :p, :e, '', false, :t, :pub, false, :c, NULL, :r, :s, :sc, CAST(:reasons AS JSON))"
            ),
            {
                "post": post_id,
                "f": facility_id,
                "p": platform,
                "e": row["external_id"],
                "t": row["original_text"],
                "pub": published,
                "c": row["collected_at"],
                "r": stars.get(row["external_id"]) if platform == "google" else None,
                "s": "visible",
                "sc": result.status,
                "reasons": __import__("json").dumps(result.reasons),
            },
        )
        created_comments += 1

        # A Google review's place id is an exact identifier: record it on the facility's Google profile.
        place_id = place_by_review.get(row["external_id"])
        if platform == "google" and place_id and facility_id is not None:
            db.execute(
                text(
                    "INSERT INTO facility_external_profiles (facility_id, platform, external_id, url, display_name, match_method, photos, details) "
                    "VALUES (:f, 'google', :pid, '', '', 'google_place_id', CAST('[]' AS JSON), CAST('{}' AS JSON)) "
                    "ON CONFLICT ON CONSTRAINT uq_external_profiles_facility_platform_id DO NOTHING"
                ),
                {"f": facility_id, "pid": place_id},
            )

    print(f"  legacy rows: {len(rows)}; posts created: {created_posts} ({unlinked} unlinked); comments created: {created_comments}; skipped: {skipped}")
