# The ReproCare bot — collection pipeline, step by step

This traces what actually happens, end to end, and which file does it. The technologies are the ones the
earlier integration build used: **Google Places API (New)**, **Playwright** (Facebook and facility websites),
**Apify** (TikTok). One entrypoint: `browser_bot/reprocare_bot.py`.

```
 Google Places ──► facilities + Google profile (place id, rating, count, photo refs)
        │                         │
        │ website                 │ Place Details reviews
        ▼                         ▼
 facility website ──► Facebook page ──► posts ──► comments ─┐
 (Playwright)          (official link or        (Playwright) │
                        one exact public match)              ├─► staging/batches/*.json ─► importer ─► external_posts
 Apify TikTok search ──► videos naming the facility ──► comments (Apify) ─┘   (private)    (same rules     external_comments
                                                                                            as the API)        │
                                                                         facility page ◄── /api/facilities/{slug}/public-feedback …
```

## 1. How facilities are discovered
`reprocare_bot.py discover --apply` → `google_places.text_search()` (Text Search, `regionCode=KE`, up to 20 places per query, field mask in `SEARCH_FIELDS`) → `facilities.upsert_from_place()`.
* Only places whose name/types make them a hospital, clinic, maternity home, health centre or laboratory are kept (`google_places.facility_type`, extended from the legacy scripts' `expand_facilities.facility_type`). Permanently closed places are skipped.
* Town and county come from Google's `addressComponents` (the legacy importer wrote "Nairobi" for everything). Opening hours come from `regularOpeningHours`.
* **No duplicates:** a place is matched by Google place id — on the facility's Google profile, or in `facilities.external_id` where the legacy importer stored it. Never by name. Values are only filled in when empty, so details edited by facility staff are kept.

## 2. How websites and social pages are identified
* **Website:** Google's `websiteUri`.
* **Facebook page** (`facebook_pages.find_official_page`): first, Facebook links published on the facility's own homepage (Playwright, the legacy scripts' `find_social_links`) → `match_method = official_website`. Only if none: the legacy scripts' public-search fallback (Bing RSS) accepted **only when exactly one** page title contains the full facility name with health context → `public_search_exact`. Ambiguous → nothing. The chosen page is stored on `facility_external_profiles` so later runs reuse it.

## 3. How Facebook posts are located
`facebook_collector.find_posts()` (the legacy scripts' `facebook_post_finder`): opens the page in the signed-in persistent profile, scrolls at most 4 times, collects `a[href*="/posts/"]`, strips tracking parameters, then `official_posts()` keeps only posts on **that** page (the legacy scripts' rule, including its KNH alias). The page's `og:title` gives the page name. `--max-posts` 1–5 (default 2).

## 4. How comments inside those posts are collected
`facebook_collector.collect_post()` — the legacy scripts' extraction, unchanged: each visible `[role="article"]` with a "Reply" control; the comment text is the 3rd `[dir="auto"]` element and must equal the 4th; at most 30 articles. Added, each isolated so it cannot break the above:
* author and approximate time from the article's `aria-label` ("Comment by NAME 3 weeks ago") — stored with `published_at_approximate = true`;
* replies are attached to the preceding top-level comment; a reply whose author equals the page name is flagged `author_is_facility` (shown as "Facility reply");
* post context from `og:description` (post text) and `og:image` (thumbnail).
A login wall is reported as `login_required` (run `facebook-login` once — you sign in yourself; the bot never handles credentials).

## 5. How TikTok videos and their comments are collected
`tiktok_collector.collect_for_facility()` — the legacy scripts' actors and limits: `epctex~tiktok-search-scraper` (≤10 results per term; terms = facility name, and name + town) → keep a video **only if its caption contains the facility's full name** → `socialdataapi~tiktok-comments-scraper` (≤2 videos, ≤10 top-level comments, ≤2 replies each). Video caption, creator, cover and date are kept from the search record (the legacy scripts discarded them). Comment id `cid`, text, `createTimeISO`, likes and replies are normalised in `comments_from_dataset()`; comments belonging to another video are dropped.

## 6. How Apify and Playwright are used
* **Playwright:** facility websites (headless Chromium), Facebook pages and posts (persistent profile in `REPROCARE_BOT_HOME/facebook`). `REPROCARE_BOT_BROWSER_PATH` can point at an installed Chrome.
* **Apify:** synchronous actor runs (`run-sync-get-dataset-items?timeout=120`, client timeout 135 s, Bearer token header — all as in the legacy scripts). The legacy scripts' `/v2/actors/…` path is tried first; only an HTTP 404 triggers one retry on the documented `/v2/acts/…` path. 401/403/429/5xx are reported, not retried. The endpoint is logged; the token is not. Runs are billable: `tiktok` refuses to run without `--allow-paid-apify`.

## 7. How Google Places obtains hospital information
`reprocare_bot.py google` → `place_details()` with `DETAIL_FIELDS`: id, name, address, components, location, types, website, phone, Maps URL, **rating, userRatingCount, regularOpeningHours, reviews, photos**, business status. Stored: rating and count on the facility's Google profile (attributed to Google, never mixed with ReproCare's rating), photo **references** (resource names + author attributions — photos are not downloaded), and Google's reviews (Google returns at most 5, chosen by Google) as one "listing" with its reviews. Billing: these fields fall in Google's higher-priced SKUs; requests are capped per day (`REPROCARE_PLACES_DAILY_LIMIT`, default 25) and responses cached for 30 days in a private SQLite file.

## 8. How collected information is normalised and stored
Every collector produces the same batch shape — one post/video/listing plus its comments — written privately (0600) to `staging/batches/<platform>/<facility>__<post>.json`, then imported by `importer.import_direct()` (or over HTTP with `--api` and `IMPORT_API_KEY`) through `app.services.external_feedback_service.import_batches` — the same code the `POST /api/import/external-feedback` endpoint uses. Text is stored exactly as collected. Screening records reasons with each comment. Phone numbers and email addresses inside comments are masked when shown to visitors. Empty comments are skipped.

Facebook posts and new Facebook comments await an admin decision at `/dashboard/admin/facebook-feedback`. Admins review the original post, stored profile associations, and individual comments. Publishing requires a note, explicit comment selection, and facility or organization attribution. Use facility attribution only when the evidence identifies that location. Use organization attribution when evidence links the post to the organization and the branch is unspecified. Withhold the post when the source, organization, or context cannot be confirmed. Public Facebook feedback is unverified and excluded from ReproCare ratings. See [the Facebook attribution audit](FACEBOOK_FEEDBACK_AUDIT.md).

## 9. How duplicates are identified
* posts: unique `(platform, external_id)` — Facebook `sha256(post url)[:32]`, TikTok video id, Google place id;
* comments: unique `(platform, external_id)` — Facebook `sha256(post url + "\n" + text)` (the legacy scripts' fingerprint, so migrated and new data de-duplicate against each other), TikTok `cid`, Google review resource name / Apify `reviewId`;
* re-running any step or re-importing the same files changes nothing (tested).

## 10. How feedback is associated with the correct hospital
The bot always collects **for one facility at a time** and imports with that facility's slug; Google data is linked by place id. Rules enforced on import (`resolve_facility`): slug or place id only; a post already attributed to one facility is never moved to another. The legacy scripts' staged files only carry a hospital *name*; they are imported only when that name equals exactly **one** facility name (case and spacing ignored) — otherwise they are reported as unresolved and not stored. Rows migrated from the legacy scripts' database that cannot be linked are kept but not shown (`facility_id` empty); `report` counts them. Link one by setting `external_posts.facility_id` (and its comments') in the database.

## 11. How the frontend retrieves and displays it
* `GET /api/facilities/{slug}/public-feedback` — counts per platform, Google rating (attributed), linked accounts, last run per platform.
* `GET /api/facilities/{slug}/public-feedback/posts?platform=&page=&page_size=` — posts/videos/listings with ≥1 visible comment, newest first, each with a 3-comment preview (page size ≤ 20).
* `GET /api/external-posts/{id}/comments?page=&page_size=` — top-level comments with their replies nested (page size ≤ 40).
`components/PublicFeedback.jsx` renders these on the facility page under "Public feedback from social media and Google": platform filter, post/video context with a link to the original, comment threads loaded on demand with their own pagination, loading/empty/error states. Author names are shortened to "First L." (facility accounts keep their name). The ReproCare rating in the hero and in search is computed from `reviews` only — see `services/facility_service.py`, unchanged.

### Instagram local demo captures

Meta requires express permission for automated Instagram collection. The custom
Playwright adapter processes authorized local HTML captures offline. It launches
a fresh context and blocks scripts and network requests. It never uses an
Instagram session or Apify. Authorized capture files represent each post as
`article[data-instagram-permalink]`, with `[data-caption]` and optional
`[data-comment][data-author]` elements. Use it only for an independently
confirmed facility and Instagram account whose content you are authorized to
display. Private captures and normalized output belong outside the checkout.
The local demo reads normalized output through `REPROCARE_INSTAGRAM_DEMO_CAPTURE`.
The adapter does not import to PostgreSQL or automate Instagram's live site.
