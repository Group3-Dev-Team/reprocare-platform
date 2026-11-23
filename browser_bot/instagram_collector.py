"""Convert an authorized HTML capture to the private local Instagram demo format.

This command processes a supplied file in a fresh Playwright context with scripts
and network requests disabled. The organization must be authorized to share the
post and comment text. No Instagram login, session, remote automation or Apify.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from bot_config import ROOT, launch_kwargs  # also adds backend to sys.path
from app.services.instagram_capture import InstagramPost, MAX_CAPTURE_BYTES


def collect_capture(html: str, slug: str, account: str) -> list[InstagramPost]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs(headless=True))
        try:
            context = browser.new_context(java_script_enabled=False, offline=True, service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            return [
                InstagramPost(
                    facility_slug=slug, account=account, url=post.get_attribute("data-instagram-permalink") or "",
                    caption="\n".join(post.locator("[data-caption]").all_text_contents()).strip(),
                    captured_at=datetime.now(timezone.utc).isoformat(),
                    comments=[
                        {"author": node.get_attribute("data-author") or "Instagram user", "text": node.inner_text().strip()}
                        for node in post.locator("[data-comment]").all() if node.inner_text().strip()
                    ],
                )
                for post in page.locator("article[data-instagram-permalink]").all()
            ]
        finally:
            browser.close()


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("capture", type=Path)
    args.add_argument("output", type=Path)
    args.add_argument("--facility", required=True)
    args.add_argument("--account", required=True)
    args.add_argument("--authorized-capture", required=True, action="store_true",
                      help="Confirm permission to use and display this capture for the specified listing")
    config = args.parse_args()
    out = config.output.resolve()
    if out.is_relative_to(ROOT):
        args.error("The capture output must be kept outside the project checkout.")
    with config.capture.open("rb") as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    if len(raw) > MAX_CAPTURE_BYTES:
        args.error("The capture exceeds the local demo limit.")
    items = collect_capture(raw.decode("utf-8"), config.facility, config.account)
    if not items:
        args.error("The capture has no supported post markup.")
    content = json.dumps([item.model_dump() for item in items], ensure_ascii=False)
    if len(content.encode()) > MAX_CAPTURE_BYTES:
        args.error("Normalized capture exceeds the local demo limit.")
    with os.fdopen(os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w", encoding="utf-8") as stream:
        stream.write(content)
    print(f"Captured {len(items)} authorized Instagram posts for local preview.")


if __name__ == "__main__":
    main()
