"""Facebook post discovery and comment collection with Playwright (the legacy scripts' facebook_post_finder.py and
facebook_collector.py, preserved).

<<<<<<< HEAD
The core comment extraction is the legacy scripts', unchanged: inside each visible comment `[role="article"]` that has
a "Reply" control, the comment text is the 3rd `[dir="auto"]` element and must equal the 4th.
=======
Inside each visible comment article with a "Reply" control, the third and fourth own
`[dir="auto"]` elements must contain the same text. Replies are associated by nesting
or by a permalink that identifies their parent on the same post.
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68

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
<<<<<<< HEAD
from facebook_pages import FACEBOOK_HOSTS, KNOWN_PAGE_ALIASES
=======
from facebook_pages import FACEBOOK_HOSTS, KNOWN_PAGE_ALIASES, page_slug
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68

AGE = re.compile(
    r"^(?P<kind>Comment|Reply) by (?P<name>.+?)\s+(?P<n>a|an|\d+)\s+(?P<unit>second|minute|hour|day|week|month|year)s?\s+ago\b",
    re.IGNORECASE,
)
UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2629800, "year": 31557600}
<<<<<<< HEAD
=======
MORE_COMMENTS = re.compile(
    r"^(?:View|See) (?:(?:all|more|previous) |\d+ |\d+ (?:more|previous) |all \d+ )?(?:comments|repl(?:y|ies))$",
    re.I,
)
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68


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
<<<<<<< HEAD
=======
    slug = page_slug(page_url)
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
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
<<<<<<< HEAD
                for href in page.locator('a[href*="/posts/"]').evaluate_all("(els) => els.map(e => e.href)"):
                    clean = clean_post_url(href)
                    if clean:
                        posts.add(clean)
=======
                found = []
                for href in page.locator('a[href*="/posts/"]').evaluate_all("(els) => els.map(e => e.href)"):
                    clean = clean_post_url(href)
                    if clean:
                        found.append(clean)
                posts.update(official_posts(found, slug) if slug else found)
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
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


<<<<<<< HEAD
=======
def _expand_comments(page, limit: int) -> None:
    """Follow a bounded number of read-only controls for already accessible threads."""
    from playwright.sync_api import TimeoutError as PWTimeout

    articles = page.locator('[role="article"]:visible')
    controls = page.get_by_role("button", name=MORE_COMMENTS).filter(visible=True)
    for _ in range(5):
        count = articles.count()
        if count >= limit or not controls.count():
            break
        try:
            controls.first.click(timeout=1500)
            articles.nth(count).wait_for(state="visible", timeout=1500)
        except PWTimeout:
            break


def _comment_articles(page, post_url: str, limit: int) -> list[dict]:
    return page.locator('[role="article"]:visible').evaluate_all(
        """(articles, {postUrl, limit, facebookHosts}) => {
            const post = new URL(postUrl);
            const path = url => url.pathname.replace(/\\/$/, "");
            const indices = new Map(articles.map((article, index) => [article, index]));
            return articles.slice(0, limit).flatMap((article, index) => {
                const own = selector => Array.from(article.querySelectorAll(selector))
                    .filter(node => node.closest('[role="article"]') === article);
                const label = article.getAttribute("aria-label") || "";
                const fields = own('[dir="auto"]');
                if (fields.length < 4 || !own('button, [role="button"], span, div, a').some(
                    node => node.innerText?.trim() === "Reply"
                )) return [];
                const text = fields[2].innerText.trim();
                if (!text || text !== fields[3].innerText.trim()) return [];

                const links = new Map();
                for (const link of own('a[href*="comment_id="]')) {
                    if (!URL.canParse(link.href)) continue;
                    const url = new URL(link.href);
                    const sameHost = url.host === post.host ||
                        (facebookHosts.includes(url.hostname) && facebookHosts.includes(post.hostname));
                    if (!sameHost || path(url) !== path(post)) continue;
                    const comment = url.searchParams.get("comment_id");
                    const reply = url.searchParams.get("reply_comment_id");
                    if (comment) links.set(JSON.stringify([comment, reply]), [comment, reply]);
                }
                const [comment, reply] = links.size === 1 ? links.values().next().value : [null, null];
                return [{
                    index, label, text, comment, reply,
                    ancestor: indices.get(article.parentElement.closest('[role="article"]')) ?? null
                }];
            });
        }""",
        {"postUrl": post_url, "limit": limit, "facebookHosts": sorted(FACEBOOK_HOSTS)},
    )


def _linked_comments(articles: list[dict], post_url: str, page_name: str, now: datetime) -> tuple[list[dict], int]:
    comments = {}
    native_ids = {}
    seen = set()
    for article in articles:
        text = article["text"]
        identifier = hashlib.sha256((post_url + "\n" + text).encode("utf-8")).hexdigest()
        if identifier in seen:
            continue
        seen.add(identifier)
        comments[article["index"]] = (identifier, article, parse_aria_label(article["label"], now))
        native_id = article["reply"] or article["comment"]
        if native_id:
            native_ids[native_id] = article["index"]

    parents = {}
    for index, (_, article, meta) in comments.items():
        parent = article["ancestor"]
        if parent not in comments:
            parent = native_ids.get(article["comment"]) if article["reply"] else None
        if parent != index and parent in comments:
            parents[index] = parent
        elif meta["is_reply"] or article["reply"]:
            parents[index] = None

    captured = []
    unlinked = 0
    for index, (identifier, article, meta) in comments.items():
        # A reply with a missing or cyclic thread cannot be imported as a top-level comment.
        thread = set()
        cursor = index
        while cursor is not None and cursor in parents and cursor not in thread:
            thread.add(cursor)
            cursor = parents[cursor]
        if cursor is None or cursor in thread:
            unlinked += 1
            continue
        parent = parents.get(index)
        author = meta["author"]
        captured.append(
            {
                "external_id": identifier,
                "parent_external_id": comments[parent][0] if parent is not None else None,
                "author_name": author,
                "author_is_facility": bool(page_name and author and author.casefold() == page_name.casefold()),
                "text": article["text"],
                "published_at": meta["published_at"],
                "published_at_approximate": meta["published_at"] is not None,
                "collected_at": now.isoformat(),
            }
        )
    return captured, unlinked


>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
def collect_post(post_url: str, page_name: str = "", max_comments: int = 100) -> dict:
    """Collect one post's context and visible comments. Returns {'post': {...}, 'comments': [...], 'status': str}."""
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright

<<<<<<< HEAD
    collected_at = datetime.now(timezone.utc).isoformat()
    post = {"url": post_url, "caption": "", "thumbnail_url": "", "author_name": page_name}
    comments, seen = [], set()
=======
    now = datetime.now(timezone.utc)
    post = {"url": post_url, "caption": "", "thumbnail_url": "", "author_name": page_name}
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68

    with sync_playwright() as p:
        context = _context(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
<<<<<<< HEAD
                page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            except PWTimeout:
                return {"post": post, "comments": [], "status": "unreachable"}

            post["caption"] = _meta(page, "og:description")
            image = _meta(page, "og:image")
            post["thumbnail_url"] = image if image.startswith("https://") else ""
            if needs_login(page.url):
                return {"post": post, "comments": [], "status": "login_required"}

=======
                response = page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            except PWTimeout:
                return {"post": post, "comments": [], "status": "unreachable"}

            if needs_login(page.url):
                return {"post": post, "comments": [], "status": "login_required"}
            if response is None or not response.ok:
                return {"post": post, "comments": [], "status": "unreachable"}
            post["caption"] = _meta(page, "og:description")
            image = _meta(page, "og:image")
            post["thumbnail_url"] = image if image.startswith("https://") else ""

            _expand_comments(page, max_comments)
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68
            try:
                page.get_by_text("Reply", exact=True).first.wait_for(state="visible", timeout=20000)
            except PWTimeout:
                return {"post": post, "comments": [], "status": "no_comments_visible"}

<<<<<<< HEAD
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
=======
            articles = _comment_articles(page, post_url, max_comments)
        finally:
            context.close()

    comments, unlinked = _linked_comments(articles, post_url, page_name, now)
    return {
        "post": post, "comments": comments, "status": "ok" if comments else "no_comments_visible",
        "unlinked_replies": unlinked,
    }
>>>>>>> 7d1aa0c985beb916cfb0006f09d64bdd4e41ab68


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
