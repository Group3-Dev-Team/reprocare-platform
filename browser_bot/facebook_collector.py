"""Facebook post discovery and comment collection with Playwright (the legacy scripts' facebook_post_finder.py and
facebook_collector.py, preserved).

The core comment extraction is the legacy scripts', unchanged: inside each visible comment `[role="article"]` that has
a "Reply" control, the comment text is the 3rd `[dir="auto"]` element and must equal the 4th.

Added (best effort, each step isolated so it can never break the extraction above):
* author and age from the comment article's aria-label ("Comment by NAME 3 weeks ago");
* post context from the page's Open Graph tags (og:description = post text, og:image = thumbnail);
* the page name, so replies posted by the facility's own page are labelled as facility replies.

Uses the persistent browser profile in REPROCARE_BOT_HOME/facebook. Sign in once with
`python reprocare_bot.py facebook-login`; the bot never types credentials.
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

from bot_config import FACEBOOK_PROFILE, launch_kwargs, private_dir
from facebook_pages import FACEBOOK_HOSTS, KNOWN_PAGE_ALIASES

AGE = re.compile(
    r"^(?P<kind>Comment|Reply) by (?P<name>.+?)\s+(?P<n>a|an|\d+)\s+(?P<unit>second|minute|hour|day|week|month|year)s?\s+ago\b",
    re.IGNORECASE,
)
UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2629800, "year": 31557600}


def parse_aria_label(label: str, now: datetime | None = None) -> dict:
    """'Comment by Jane Doe 3 weeks ago' -> {'author': 'Jane Doe', 'is_reply': False, 'published_at': <approx>}."""
    match = AGE.match((label or "").strip())
    if not match:
        by = re.match(r"^(Comment|Reply) by (.+)$", (label or "").strip(), re.IGNORECASE)
        return {"author": by.group(2).strip() if by else "", "is_reply": bool(by and by.group(1).lower() == "reply"), "published_at": None}
    n = 1 if match["n"].lower() in {"a", "an"} else int(match["n"])
    now = now or datetime.now(timezone.utc)
    return {
        "author": match["name"].strip(),
        "is_reply": match["kind"].lower() == "reply",
        "published_at": (now - timedelta(seconds=n * UNIT_SECONDS[match["unit"].lower()])).isoformat(),
    }


def clean_post_url(href: str) -> str | None:
    parsed = urlparse(href)
    if (parsed.hostname or "").lower() not in FACEBOOK_HOSTS or "/posts/" not in parsed.path:
        return None
    return urlunparse(("https", "web.facebook.com", parsed.path, "", "", ""))  # strip tracking parameters


def official_posts(posts: list[str], slug: str) -> list[str]:
    """Keep only posts published on the facility's matched page (legacy scripts)."""
    accepted = []
    for url in posts:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) >= 3 and parts[1].lower() == "posts" and KNOWN_PAGE_ALIASES.get(parts[0].lower(), parts[0].lower()) == slug:
            accepted.append(url)
    return list(dict.fromkeys(accepted))


def _context(p):
    private_dir(FACEBOOK_PROFILE)
    return p.chromium.launch_persistent_context(user_data_dir=str(FACEBOOK_PROFILE), **launch_kwargs())


def needs_login(url: str) -> bool:
    return "/login" in url or "checkpoint" in url


def find_posts(page_url: str, limit: int = 5) -> tuple[list[str], str, bool]:
    """Return (post urls, page display name, login_required). Bounded scrolling, as in the legacy scripts."""
    from playwright.sync_api import sync_playwright

    posts, page_name = set(), ""
    with sync_playwright() as p:
        context = _context(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            if needs_login(page.url):
                return [], "", True
            try:
                page_name = (page.locator('meta[property="og:title"]').first.get_attribute("content", timeout=3000) or "").strip()
            except Exception:
                page_name = ""
            for _ in range(12):
                for href in page.locator('a[href*="/posts/"]').evaluate_all("(els) => els.map(e => e.href)"):
                    clean = clean_post_url(href)
                    if clean:
                        posts.add(clean)
                if len(posts) >= limit:
                    break
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(2000)
        finally:
            context.close()
    return sorted(posts)[:limit], page_name, False


def _meta(page, prop: str) -> str:
    try:
        return (page.locator(f'meta[property="{prop}"]').first.get_attribute("content", timeout=2000) or "").strip()
    except Exception:
        return ""


def collect_post(post_url: str, page_name: str = "", max_comments: int = 100) -> dict:
    """Collect one post's context and visible comments. Returns {'post': {...}, 'comments': [...], 'status': str}."""
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright

    collected_at = datetime.now(timezone.utc).isoformat()
    post = {"url": post_url, "caption": "", "thumbnail_url": "", "author_name": page_name}
    comments, seen = [], set()

    with sync_playwright() as p:
        context = _context(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            except PWTimeout:
                return {"post": post, "comments": [], "status": "unreachable"}

            post["caption"] = _meta(page, "og:description")
            image = _meta(page, "og:image")
            post["thumbnail_url"] = image if image.startswith("https://") else ""
            if needs_login(page.url):
                return {"post": post, "comments": [], "status": "login_required"}

            try:
                page.get_by_text("Reply", exact=True).first.wait_for(state="visible", timeout=20000)
            except PWTimeout:
                return {"post": post, "comments": [], "status": "no_comments_visible"}

            articles = page.locator('[role="article"]:visible')
            last_top_level = None
            for i in range(min(articles.count(), max_comments)):
                article = articles.nth(i)
                if not article.get_by_text("Reply", exact=True).count():
                    continue
                elements = article.locator('[dir="auto"]')
                if elements.count() < 4:
                    continue
                text = elements.nth(2).inner_text().strip()
                duplicate = elements.nth(3).inner_text().strip()
                if not text or text != duplicate:
                    continue

                identifier = hashlib.sha256((post_url + "\n" + text).encode("utf-8")).hexdigest()
                if identifier in seen:
                    continue
                seen.add(identifier)

                meta = {"author": "", "is_reply": False, "published_at": None}
                try:
                    meta = parse_aria_label(article.get_attribute("aria-label", timeout=1000) or "")
                except Exception:
                    pass
                is_facility = bool(page_name and meta["author"] and meta["author"].casefold() == page_name.casefold())
                comments.append(
                    {
                        "external_id": identifier,
                        "parent_external_id": last_top_level if meta["is_reply"] else None,
                        "author_name": meta["author"],
                        "author_is_facility": is_facility,
                        "text": text,
                        "published_at": meta["published_at"],
                        "published_at_approximate": meta["published_at"] is not None,
                        "collected_at": collected_at,
                    }
                )
                if not meta["is_reply"]:
                    last_top_level = identifier
        finally:
            context.close()

    return {"post": post, "comments": comments, "status": "ok" if comments else "no_comments_visible"}


def login_session(start_url: str = "https://web.facebook.com/") -> None:
    """Open a VISIBLE browser on the bot's own profile so the user signs in to Facebook directly (the legacy scripts'
    facebook_session.py). The password is typed into Facebook's page only; the bot never sees, stores or logs it.
    The session (cookies) stays inside the private profile folder, which is outside the repository."""
    from playwright.sync_api import sync_playwright

    private_dir(FACEBOOK_PROFILE)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=str(FACEBOOK_PROFILE), **launch_kwargs(headless=False))
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
            input("Sign in to Facebook in the opened window, then press Enter here to save the session and close… ")
        finally:
            context.close()
