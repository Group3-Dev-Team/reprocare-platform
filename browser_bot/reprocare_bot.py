"""ReproCare bot — discover facilities and collect public feedback into the ReproCare database.

Run from the repository root with the backend virtual environment (it has Playwright installed too):

    backend/.venv/bin/python browser_bot/reprocare_bot.py status
    backend/.venv/bin/python browser_bot/reprocare_bot.py discover --query "maternity hospitals in Nairobi" --apply
    backend/.venv/bin/python browser_bot/reprocare_bot.py link-google --facility langata-hospital-nairobi --place-id ChIJ... --apply
    backend/.venv/bin/python browser_bot/reprocare_bot.py google   --all --limit 10 [--source openstreetmap] [--has-profile google]
    backend/.venv/bin/python browser_bot/reprocare_bot.py facebook-login
    backend/.venv/bin/python browser_bot/reprocare_bot.py facebook --facility aga-khan-university-hospital
    backend/.venv/bin/python browser_bot/reprocare_bot.py tiktok   --facility kenyatta-national-hospital --allow-paid-apify
    backend/.venv/bin/python browser_bot/reprocare_bot.py import   --legacy
    backend/.venv/bin/python browser_bot/reprocare_bot.py run      --all --limit 5 [--with-tiktok --allow-paid-apify]
    backend/.venv/bin/python browser_bot/reprocare_bot.py report

Every collection step stores what it found, and records a run (succeeded / empty / failed + reason) that
administrators and the facility page can see. Nothing is invented when a source returns nothing.
"""

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import bot_config
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import DataSource, ExternalComment, ExternalPost, Facility, FacilityExternalProfile
from app.services.external_feedback_service import record_run, upsert_profile

# Hard ceiling for one run. `--all` means "eligible facilities, up to --limit (default 5)", never the whole directory:
# each facility can mean billed Google/Apify requests or Facebook page loads. Run again for the next batch.
MAX_FACILITIES_PER_RUN = 50
PROFILE_PLATFORMS = ("google", "facebook", "tiktok")


def log(*parts):
    print(*parts, flush=True)


def _with_profile(platform: str):
    return Facility.id.in_(select(FacilityExternalProfile.facility_id).where(FacilityExternalProfile.platform == platform))


def select_facilities(db, slugs: list[str] | None, all_: bool, limit: int, need_google: bool = False,
                      source: str | None = None, has_profile: str | None = None, no_profile: str | None = None) -> list[Facility]:
    if slugs:
        if len(slugs) > MAX_FACILITIES_PER_RUN:
            raise SystemExit(f"Choose at most {MAX_FACILITIES_PER_RUN} facilities per run")
        found = db.scalars(select(Facility).where(Facility.slug.in_(slugs))).all()
        missing = set(slugs) - {f.slug for f in found}
        for slug in sorted(missing):
            log("Unknown facility slug:", slug)
        return list(found)
    if not all_:
        raise SystemExit("Choose facilities with --facility SLUG (repeatable) or --all")
    if limit > MAX_FACILITIES_PER_RUN:
        raise SystemExit(f"--limit can be at most {MAX_FACILITIES_PER_RUN} per run; run again for the next facilities")
    query = select(Facility).where(Facility.is_demo.is_(False)).order_by(Facility.name, Facility.id)
    if source:
        query = query.where(Facility.source_id.in_(select(DataSource.id).where(DataSource.code == source)))
    if has_profile:
        query = query.where(_with_profile(has_profile))
    if no_profile:
        query = query.where(~_with_profile(no_profile))
    if need_google:
        # a linked Google profile, or a Google place id in facilities.external_id (legacy importer); not 'osm:…' ids
        query = query.where(_with_profile("google") | Facility.external_id.like("ChIJ%"))
    return list(db.scalars(query.limit(limit)))


def selected(db, args, need_google: bool = False) -> list[Facility]:
    return select_facilities(db, args.facility, args.all, args.limit, need_google=need_google, source=args.source,
                             has_profile=args.has_profile, no_profile=args.no_profile)


def google_place_id(db, facility: Facility) -> str | None:
    profile = db.scalar(select(FacilityExternalProfile).where(FacilityExternalProfile.facility_id == facility.id, FacilityExternalProfile.platform == "google"))
    if profile:
        return profile.external_id
    if facility.external_id and facility.external_id.startswith("ChIJ"):
        return facility.external_id
    return None


def offer_login(url: str) -> bool:
    """When Facebook shows a sign-in wall in an interactive terminal, open a visible browser for the user to sign in
    themselves, then retry once. Unattended runs never prompt; they record that sign-in is needed."""
    if not sys.stdin.isatty() or os.environ.get("REPROCARE_BOT_NO_PROMPT"):
        return False
    answer = input("  Facebook asks you to sign in. Open a browser window to sign in now? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        return False
    from facebook_collector import login_session

    login_session(url)
    return True


def cmd_status(args):
    from places_cache import DAILY_LIMIT, requests_today
    from staging import legacy_batches, read_batches

    log("ReproCare bot status")
    log("  backend/.env found:          ", bot_config.ENV_FILE.is_file())
    log("  Google Places key set:       ", bool(bot_config.google_api_key()))
    log("  Apify token set:             ", bool(bot_config.apify_token()))
    log("  Import key set (for --api):  ", bool(bot_config.import_key()))
    log("  Data folder:                 ", bot_config.DATA_HOME)
    log("  Facebook profile present:    ", bot_config.FACEBOOK_PROFILE.is_dir() and any(bot_config.FACEBOOK_PROFILE.iterdir()))
    try:
        log("  Google requests today:       ", f"{requests_today()} / {DAILY_LIMIT}")
    except Exception as exc:
        log("  Google request counter:      ", type(exc).__name__)
    log("  Staged batches (new format): ", len(read_batches()))
    log("  Staged batches (legacy):     ", len(legacy_batches()))
    try:
        import playwright  # noqa: F401

        log("  Playwright installed:        ", True)
    except ImportError:
        log("  Playwright installed:        ", False, "(pip install -r browser_bot/requirements.txt && playwright install chromium)")
    with SessionLocal() as db:
        log("  Facilities (real / demo):    ", db.scalar(select(func.count()).select_from(Facility).where(Facility.is_demo.is_(False))), "/", db.scalar(select(func.count()).select_from(Facility).where(Facility.is_demo.is_(True))))
        log("  External posts / comments:   ", db.scalar(select(func.count()).select_from(ExternalPost)), "/", db.scalar(select(func.count()).select_from(ExternalComment)))


def cmd_discover(args):
    """Google Places Text Search → ReproCare facilities (the legacy scripts' import_facilities / expand_facilities)."""
    from facilities import upsert_from_place
    from google_places import PlacesUnavailable, facility_type, text_search
    from places_cache import DailyLimitReached

    queries = args.query or ["hospitals in Nairobi, Kenya", "maternity hospitals in Nairobi, Kenya", "medical clinics in Nairobi, Kenya", "health centres in Nairobi, Kenya"]
    queries = queries[: args.max_requests]
    log(f"Discovery: {len(queries)} Google Places Text Search request(s); Google bills each request.")
    if not args.apply:
        for q in queries:
            log("  would search:", q)
        log("PREVIEW ONLY — add --apply to call Google Places and save facilities.")
        return
    created = updated = skipped = 0
    with SessionLocal() as db:
        for q in queries:
            try:
                places = text_search(q)
            except (PlacesUnavailable, DailyLimitReached) as exc:
                log("  search failed:", exc)
                record_run(db, "discovery", "failed", f"{q}: {exc}")
                db.commit()
                continue
            log(f"  '{q}': {len(places)} places")
            for place in places:
                if facility_type(place) is None:
                    skipped += 1
                    continue
                facility, outcome = upsert_from_place(db, place, default_town=args.default_town)
                if outcome == "created":
                    created += 1
                    log("    + ", facility.name, "|", facility.town)
                elif outcome == "updated":
                    updated += 1
                else:
                    skipped += 1
                    if outcome.startswith("skipped:possible duplicate"):
                        log(f"    ? {place.get('displayName', {}).get('text', '')} ({place.get('id')}): {outcome[8:]} — check it, then link with"
                            f" `link-google --facility SLUG --place-id {place.get('id')} --apply`")
            record_run(db, "discovery", "succeeded" if places else "empty", f"{q}: {len(places)} places")
            db.commit()
    log(f"Facilities created: {created}, updated: {updated}, skipped: {skipped}")


def cmd_link_google(args):
    """Link a reviewed Google place id to an existing facility (for example an OpenStreetMap facility). No Google request."""
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]{10,255}", args.place_id or ""):
        raise SystemExit("That does not look like a Google place id")
    with SessionLocal() as db:
        facility = db.scalar(select(Facility).where(Facility.slug == args.facility))
        if facility is None:
            raise SystemExit(f"Unknown facility slug: {args.facility}")
        owner = db.scalar(
            select(Facility).outerjoin(FacilityExternalProfile, (FacilityExternalProfile.facility_id == Facility.id) & (FacilityExternalProfile.platform == "google"))
            .where((FacilityExternalProfile.external_id == args.place_id) | (Facility.external_id == args.place_id)).limit(1)
        )
        if owner is not None and owner.id != facility.id:
            raise SystemExit(f"That place id is already linked to {owner.slug}; nothing changed")
        log(f"Link Google place id {args.place_id} to {facility.name} ({facility.slug}, id {facility.id})")
        if owner is not None:
            log("Already linked; nothing to do.")
            return
        if not args.apply:
            log("PREVIEW ONLY — add --apply to save the link.")
            return
        upsert_profile(db, facility, "google", args.place_id, url="", match_method="manual_review")
        db.commit()
        log("Linked. `google --facility", facility.slug, "` will now refresh its Google rating.")


def cmd_google(args):
    """Place Details for each facility: Google rating, rating count and photo references. Written Google reviews are
    not stored: the facility page loads them live with attribution."""
    from facilities import upsert_from_place
    from google_places import PlacesUnavailable, place_details
    from places_cache import DailyLimitReached

    with SessionLocal() as db:
        facilities = selected(db, args, need_google=True)
        log(f"Google Places details for {len(facilities)} facilit(y/ies); one billed request each (cached {30} days).")
        for facility in facilities:
            place_id = google_place_id(db, facility)
            if not place_id:
                log("  ", facility.name, "— no Google place id; run `discover` first")
                record_run(db, "google", "skipped", "No Google place id linked to this facility", facility)
                continue
            try:
                place = place_details(place_id, refresh=args.refresh)
            except (PlacesUnavailable, DailyLimitReached) as exc:
                log("  ", facility.name, "— failed:", exc)
                record_run(db, "google", "failed", str(exc), facility)
                db.commit()
                continue
            upsert_from_place(db, place)
            has_rating = place.get("rating") is not None
            log(f"   {facility.name}: Google rating {place.get('rating')} ({place.get('userRatingCount')} ratings), {len(place.get('photos') or [])} photo references; written reviews load live on the facility page")
            record_run(db, "google", "succeeded" if has_rating else "empty", f"rating={place.get('rating')} count={place.get('userRatingCount')}", facility, posts_found=0)
            db.commit()


def cmd_facebook(args):
    from facebook_collector import collect_post, find_posts, official_posts
    from facebook_pages import find_official_page, page_slug
    from importer import import_direct
    from staging import facebook_post_id, read_batch, write_batch

    if not 1 <= args.max_posts <= 10:
        raise SystemExit("--max-posts must be between 1 and 10")
    batches = []
    with SessionLocal() as db:
        facilities = selected(db, args)
        for facility in facilities:
            log(f"\nFacebook: {facility.name}\n  website: {facility.website or 'Not available'}")
            profile = db.scalar(select(FacilityExternalProfile).where(FacilityExternalProfile.facility_id == facility.id, FacilityExternalProfile.platform == "facebook"))
            if profile:
                page_url, slug, method = profile.url, profile.external_id, profile.match_method
                log("  page (stored):", page_url)
            else:
                found = find_official_page(facility.name, facility.website)
                if not found:
                    log("  no confidently matched Facebook page")
                    record_run(db, "facebook", "empty", "No confidently matched Facebook page (website had no link; public search not unambiguous)", facility)
                    db.commit()
                    continue
                page_url, slug, method = found
                log(f"  page: {page_url} ({method})")
            try:
                discovered, page_name, login_wall = find_posts(page_url, limit=args.max_posts)
                if login_wall and offer_login(page_url):
                    discovered, page_name, login_wall = find_posts(page_url, limit=args.max_posts)
                if login_wall:
                    log("  Facebook requires sign-in — run `facebook-login` once, then try again")
                    record_run(db, "facebook", "failed", "Facebook asked to sign in; run `reprocare_bot.py facebook-login`", facility)
                    db.commit()
                    continue
            except Exception as exc:
                log("  post discovery failed:", type(exc).__name__)
                record_run(db, "facebook", "failed", f"Post discovery failed: {type(exc).__name__}", facility)
                db.commit()
                continue
            upsert_profile(db, facility, "facebook", slug, url=page_url, display_name=page_name or None, match_method=method)
            posts = official_posts(discovered, page_slug(page_url) or slug)
            log("  posts on the facility's page:", len(posts))
            collected = staged = 0
            problems = Counter()
            for post_url in posts:
                try:
                    result = collect_post(post_url, page_name=page_name, max_comments=100)
                    if result["status"] == "login_required" and offer_login(post_url):
                        result = collect_post(post_url, page_name=page_name, max_comments=100)
                except Exception as exc:
                    problems[f"collection {type(exc).__name__}"] += 1
                    continue
                if result["status"] == "login_required":
                    problems["login_required"] += 1
                    log("  Facebook asked to sign in — run `facebook-login` once")
                    break
                if result["status"] != "ok":
                    problems[result["status"]] += 1
                if result["status"] not in {"ok", "no_comments_visible"}:
                    continue
                if result.get("unlinked_replies"):
                    problems["replies without a matched parent"] += result["unlinked_replies"]
                post = result["post"]
                batch = {
                    "platform": "facebook",
                    "facility_slug": facility.slug,
                    "post": {
                        "external_id": facebook_post_id(post_url),
                        "url": post_url,
                        "author_name": post.get("author_name") or page_name,
                        "caption": post.get("caption", ""),
                        "thumbnail_url": post.get("thumbnail_url", ""),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "match_method": "facility_page_post",
                    },
                    "comments": result["comments"],
                }
                try:
                    path = write_batch(batch)
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    problems[f"staging {type(exc).__name__}"] += 1
                    continue
                if not args.no_import:
                    batches.extend(read_batch(path))
                staged += 1
                collected += len(result["comments"])
                log(f"  post URL: {post_url} | comments: {len(result['comments'])}")
            status = "succeeded" if staged else ("failed" if problems else "empty")
            notes = ", ".join(f"{reason} ({count})" for reason, count in sorted(problems.items()))
            message = f"{len(posts)} posts found, {staged} staged, {collected} comments collected"
            if notes:
                message += f"; issues: {notes}"
            record_run(db, "facebook", status, message, facility, posts_found=len(posts))
            db.commit()
    if batches and not args.no_import:
        report_import(import_direct(batches, "facebook"))


def cmd_tiktok(args):
    from importer import import_direct
    from staging import write_batch
    from tiktok_collector import ApifyUnavailable, bundle_to_batch, collect_for_facility

    if not args.allow_paid_apify:
        log("TikTok collection runs billable Apify Actors: ≤2 search runs + ≤2 comment runs per facility.")
        log("PREVIEW ONLY — add --allow-paid-apify to run them.")
        return
    batches = []
    with SessionLocal() as db:
        for facility in selected(db, args):
            log(f"\nTikTok: {facility.name}")
            try:
                bundles = collect_for_facility(facility.name, facility.town)
            except ApifyUnavailable as exc:
                log("  failed:", exc)
                record_run(db, "tiktok", "failed", str(exc), facility)
                db.commit()
                continue
            count = 0
            for bundle in bundles:
                batch = bundle_to_batch(bundle, facility.slug)
                if batch["comments"]:
                    write_batch(batch)
                    batches.append(batch)
                    count += len(batch["comments"])
            log(f"  videos whose caption names the facility: {len(bundles)}; comments: {count}")
            upsert_profile(db, facility, "tiktok", "search:" + facility.slug, url="", display_name=facility.name, match_method="caption_exact_name")
            record_run(db, "tiktok", "succeeded" if count else "empty", f"{len(bundles)} matching videos, {count} comments", facility, posts_found=len(bundles))
            db.commit()
    if batches and not args.no_import:
        report_import(import_direct(batches, "tiktok"))


def cmd_import(args):
    from importer import import_direct, import_http
    from staging import legacy_batches, read_batches

    raw = [b for _, b in read_batches()]
    if args.legacy:
        legacy = legacy_batches()
        log("Legacy staged collections found:", len(legacy))
        raw += legacy
    log("Batches to import:", len(raw))
    if not raw:
        return
    report_import(import_http(raw, args.api) if args.api else import_direct(raw, "import"))


def report_import(result: dict):
    log(f"Imported posts: {result['imported']}/{result['received']}; new comments: {result['comments_created']}; already present: {result['comments_skipped']}")
    for err in result.get("errors", []):
        log("  rejected:", err.get("error"))
    for problem in result.get("unresolved", []):
        log("  unresolved:", problem)
    if result.get("comments_unlinked"):
        log(f"  replies with a missing parent left in staging: {result['comments_unlinked']}")


def cmd_report(args):
    with SessionLocal() as db:
        rows = db.execute(
            select(Facility.name, ExternalComment.platform, ExternalComment.status, func.count())
            .join(Facility, Facility.id == ExternalComment.facility_id)
            .group_by(Facility.name, ExternalComment.platform, ExternalComment.status)
            .order_by(Facility.name)
        ).all()
        unlinked = db.scalar(select(func.count()).select_from(ExternalPost).where(ExternalPost.facility_id.is_(None)))
    log("=== REPROCARE PUBLIC FEEDBACK REPORT ===")
    for name, platform, status, n in rows:
        log(f"{name} | {platform} | {status}: {n}")
    log("Posts not linked to a facility (not shown to visitors):", unlinked)
    log("ReproCare ratings: unaffected (computed from ReproCare reviews only)")


def cmd_facebook_login(args):
    from facebook_collector import login_session

    login_session()


def cmd_run(args):
    """google → facebook → (tiktok) → report, for the same facilities."""
    args.no_import = False
    with SessionLocal() as db:
        args.facility = [f.slug for f in selected(db, args)]
    args.all = False
    if bot_config.google_api_key():
        cmd_google(args)
    else:
        log("Google Places key not set — skipping Google step")
    cmd_facebook(args)
    if args.with_tiktok:
        cmd_tiktok(args)
    cmd_report(args)


def main(argv=None):
    parser = argparse.ArgumentParser(description="ReproCare bot", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def facility_args(p):
        p.add_argument("--facility", action="append", help="facility slug (repeatable)")
        p.add_argument("--all", action="store_true", help=f"eligible real (non-demo) facilities, up to --limit (at most {MAX_FACILITIES_PER_RUN})")
        p.add_argument("--limit", type=int, default=5)
        p.add_argument("--source", help="with --all: only facilities from this data source, e.g. google_places or openstreetmap")
        p.add_argument("--has-profile", choices=PROFILE_PLATFORMS, help="with --all: only facilities already linked to this platform")
        p.add_argument("--no-profile", choices=PROFILE_PLATFORMS, help="with --all: only facilities not yet linked to this platform")
        p.add_argument("--no-import", action="store_true", help="stage files only; import later with `import`")

    sub.add_parser("status")
    p = sub.add_parser("discover")
    p.add_argument("--query", action="append")
    p.add_argument("--max-requests", type=int, default=4)
    p.add_argument("--default-town", default="")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("link-google", help="link a reviewed Google place id to an existing facility (no Google request)")
    p.add_argument("--facility", required=True)
    p.add_argument("--place-id", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("google")
    facility_args(p)
    p.add_argument("--refresh", action="store_true", help="ignore the 30-day cache")
    p = sub.add_parser("facebook")
    facility_args(p)
    p.add_argument("--max-posts", type=int, default=10)
    p = sub.add_parser("tiktok")
    facility_args(p)
    p.add_argument("--allow-paid-apify", action="store_true")
    p = sub.add_parser("import")
    p.add_argument("--legacy", action="store_true", help="also import staged collections from the legacy scripts")
    p.add_argument("--api", help="import over HTTP to this API base URL instead of writing to the database")
    sub.add_parser("report")
    sub.add_parser("facebook-login")
    p = sub.add_parser("run")
    facility_args(p)
    p.add_argument("--max-posts", type=int, default=10)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--with-tiktok", action="store_true")
    p.add_argument("--allow-paid-apify", action="store_true")

    args = parser.parse_args(argv)
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be at least 1")
    {
        "status": cmd_status,
        "discover": cmd_discover,
        "link-google": cmd_link_google,
        "google": cmd_google,
        "facebook": cmd_facebook,
        "tiktok": cmd_tiktok,
        "import": cmd_import,
        "report": cmd_report,
        "facebook-login": cmd_facebook_login,
        "run": cmd_run,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
