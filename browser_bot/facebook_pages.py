"""Identify a facility's official Facebook page (from the legacy scripts: google_places_discovery.find_social_links,
facebook_page_search.search_facebook_page, run_hospital_bot.facebook_page_slug).

Order of evidence, strongest first:
  1. a Facebook link published on the facility's own website           -> match_method 'official_website'
  2. exactly ONE public-search result whose title contains the full name -> match_method 'public_search_exact'
Nothing else is accepted. Ambiguous results are rejected, not guessed.
"""

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urljoin, urlparse

FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "web.facebook.com", "m.facebook.com"}
NOT_PAGES = {"posts", "groups", "watch", "reel", "share", "events", "marketplace", "pages", "sharer", "sharer.php", "dialog", "plugins", "tr", "login", "profile.php"}

# Previously verified: both KNH Facebook links redirect to the same hospital page.
KNOWN_PAGE_ALIASES = {"kenyatta-national-hospital-222808627792716": "kenyattanationalhospital"}


def page_slug(url: str) -> str | None:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() not in FACEBOOK_HOSTS:
        return None
    slug = parsed.path.strip("/").split("/")[0].lower()
    if not slug or slug in NOT_PAGES:
        return None
    return KNOWN_PAGE_ALIASES.get(slug, slug)


def links_from_website(website: str) -> list[str]:
    """Facebook links on the facility's own homepage (Playwright, as in the legacy scripts)."""
    from playwright.sync_api import sync_playwright

    from bot_config import launch_kwargs

    parsed = urlparse(website or "")
    if parsed.scheme not in ("http", "https"):
        return []
    links = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs(headless=True))
        try:
            page = browser.new_page()
            page.goto(website, wait_until="commit", timeout=20000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            for href in page.locator("a[href]").evaluate_all("(els) => els.map(e => e.getAttribute('href'))"):
                if not href:
                    continue
                url = urljoin(page.url, href)
                if (urlparse(url).hostname or "").lower() in FACEBOOK_HOSTS and page_slug(url):
                    links.add(url)
        finally:
            browser.close()
    return sorted(links)


def _normalize(value: str) -> str:
    value = unescape(re.sub(r"<[^>]*>", " ", value)).casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(w for w in value.split() if w not in {"the", "main", "kenya", "nairobi"})


def search_public_page(facility_name: str) -> list[str]:
    """The legacy scripts' Bing RSS fallback: accept only one unambiguous page whose title contains the exact name."""
    query = f'site:facebook.com "{facility_name}" hospital Kenya'
    endpoint = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "format": "rss"})
    try:
        request = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0 ReproCareDiscovery/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            root = ET.fromstring(response.read(300000))
    except Exception as exc:
        print("  public search unavailable:", type(exc).__name__)
        return []

    expected = _normalize(facility_name)
    candidates = []
    for item in root.findall(".//item"):
        url = (item.findtext("link") or "").strip()
        title = item.findtext("title") or ""
        description = item.findtext("description") or ""
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in FACEBOOK_HOSTS:
            continue
        if len(parts) != 1 or not page_slug(url):
            continue
        if expected not in _normalize(title):
            continue
        if not any(t in (title + " " + description).casefold() for t in ("hospital", "health", "clinic", "kenya", "nairobi", "medical")):
            continue
        candidates.append(url)
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        if candidates:
            print("  public search: ambiguous (", len(candidates), "pages ) — not used")
        return []
    return candidates


def find_official_page(facility_name: str, website: str | None) -> tuple[str, str, str] | None:
    """Returns (page_url, page_slug, match_method) or None."""
    links = []
    if website:
        try:
            links = links_from_website(website)
        except Exception as exc:
            print("  website lookup unavailable:", type(exc).__name__)
    method = "official_website"
    if not links:
        links = search_public_page(facility_name)
        method = "public_search_exact"
    pages = {}
    for link in links:
        slug = page_slug(link)
        if slug and slug not in pages:
            pages[slug] = link
    if not pages:
        return None
    if len(pages) > 1 and method == "official_website":
        # A website can link several pages (e.g. a group page and a branch); prefer the one named like the facility.
        target = _normalize(facility_name).replace(" ", "")
        ranked = sorted(pages.items(), key=lambda kv: (target[:8] not in kv[0].replace("-", "").replace(".", ""), kv[0]))
        slug, url = ranked[0]
    else:
        slug, url = next(iter(pages.items()))
    return url, slug, method
