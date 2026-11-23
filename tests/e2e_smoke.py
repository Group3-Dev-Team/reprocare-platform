"""Browser smoke test of the main journeys against a running stack.

Prerequisites: backend on http://localhost:8000 with the demo seed, frontend on http://localhost:5173,
and `pip install playwright && playwright install chromium`.
Set SMOKE_STAFF_PASSWORD and SMOKE_ADMIN_PASSWORD to the demo account passwords from your local seed
(SMOKE_STAFF_EMAIL and SMOKE_ADMIN_EMAIL default to the demo addresses).

    python tests/e2e_smoke.py [--chrome /path/to/chrome]
"""

import asyncio
import os
import random
import sys
from datetime import date, timedelta

from playwright.async_api import async_playwright, expect

BASE = "http://localhost:5173"
expect.set_options(timeout=10_000)
STAFF = (os.environ.get("SMOKE_STAFF_EMAIL", "staff@reprocare.demo"), os.environ.get("SMOKE_STAFF_PASSWORD", ""))
ADMIN = (os.environ.get("SMOKE_ADMIN_EMAIL", "admin@reprocare.demo"), os.environ.get("SMOKE_ADMIN_PASSWORD", ""))
CHROME = sys.argv[sys.argv.index("--chrome") + 1] if "--chrome" in sys.argv else None


async def sign_in(page, email, password):
    await page.goto(f"{BASE}/sign-in")
    await page.get_by_label("Email address").fill(email)
    await page.locator("input[autocomplete=current-password]").fill(password)
    await page.get_by_role("button", name="Sign in").click()
    await page.wait_for_url("**/dashboard**")


async def sign_out(page):
    """Sign out from the dashboard sidebar, or from the account menu on public pages (v2.0)."""
    direct = page.get_by_role("button", name="Sign out")
    if await direct.count():
        await direct.first.click()
    else:
        await page.locator(".user-menu-trigger:visible").first.click()
        await page.get_by_role("menuitem", name="Sign out").click()


async def main():
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page = await (await browser.new_context(viewport={"width": 1280, "height": 900})).new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 1. Every public route opens and every header dropdown link resolves to a real page.
        await page.goto(BASE)
        links = await page.eval_on_selector_all(".dropdown-link, .footer-col a", "els => [...new Set(els.map(e => e.getAttribute('href')))]")
        for href in links:
            await page.goto(BASE + href)
            await expect(page.locator("h1").first).to_be_visible()
            assert "could not find that page" not in (await page.locator("h1").first.inner_text()), href
        print(f"ok  {len(links)} navigation links open")

        # 2. Removed commercial routes are gone.
        for old in ("/partner", "/business-solutions", "/list-facility", "/careers"):
            await page.goto(BASE + old)
            await expect(page.get_by_text("We could not find that page")).to_be_visible()
        print("ok  commercial routes removed")

        # 3. Protected route redirects to sign-in.
        await page.goto(f"{BASE}/dashboard/appointments")
        await expect(page).to_have_url(f"{BASE}/sign-in?next=%2Fdashboard%2Fappointments")
        print("ok  protected route redirects")

        # 4. Search, filter and paginate.
        await page.goto(f"{BASE}/find-care/facilities?service=antenatal")
        await expect(page.locator(".results-count")).to_contain_text("facilities")
        await page.goto(f"{BASE}/find-care/facilities")
        await expect(page.locator(".facility-card")).to_have_count(15)  # PAGE_SIZE in FindCarePage.jsx
        await page.get_by_role("button", name="2", exact=True).click()
        await expect(page).to_have_url(f"{BASE}/find-care/facilities?page=2")
        await page.goto(f"{BASE}/find-care/facilities?q=zzzz")
        await expect(page.get_by_text("No facilities match all of these filters")).to_be_visible()
        print("ok  search, pagination and empty state")

        # 5. Register a patient, save a facility, request an appointment.
        email = f"e2e{random.randint(1000, 99999)}@example.com"
        await page.goto(f"{BASE}/register")
        await page.get_by_label("Full name").fill("Esther Wanjiku")
        await page.get_by_label("Email address").fill(email)
        await page.locator("input[autocomplete=new-password]").nth(0).fill("Passw0rd!")
        await page.get_by_label("Confirm password").fill("Passw0rd!")
        await page.get_by_role("checkbox").check()
        await page.get_by_role("button", name="Create account").click()
        await expect(page.get_by_role("heading", name="Hello, Esther")).to_be_visible()

        await page.goto(f"{BASE}/facilities/mwangaza")
        await page.get_by_role("button", name="Save", exact=True).click()
        await expect(page.get_by_text("saved to your list")).to_be_visible()
        await page.get_by_role("button", name="Request appointment").click()
        await page.get_by_label("Preferred date").fill((date.today() + timedelta(days=20)).isoformat())
        await page.get_by_label("Phone number").fill("+254711222333")
        await page.get_by_role("button", name="Send request").click()
        await expect(page.get_by_role("heading", name="Request sent")).to_be_visible()
        reference = await page.locator(".confirmation strong").first.inner_text()
        await page.get_by_role("button", name="Done").click()
        await page.reload()  # data persisted on the server, not just in React state
        await page.goto(f"{BASE}/dashboard/appointments")
        await expect(page.get_by_text(reference, exact=False)).to_be_visible()
        await expect(page.get_by_text("Awaiting facility").first).to_be_visible()
        print(f"ok  appointment {reference} requested and persisted")

        # 6. Programme registration.
        await page.goto(f"{BASE}/health-community/programmes")
        await page.locator(".program-card h3 a").nth(2).click()
        await page.get_by_role("button", name="Register for this programme").click()
        dialog = page.get_by_role("dialog")
        await dialog.locator("input[type=tel]").fill("+254711222333")
        await dialog.get_by_role("checkbox").check()
        await page.get_by_role("button", name="Register", exact=True).click()
        await expect(page.get_by_role("heading", name="You are registered")).to_be_visible()
        print("ok  programme registration")

        # 7. Sign out; the session is invalid afterwards.
        await page.get_by_role("button", name="Done").click()
        await sign_out(page)
        await page.goto(f"{BASE}/dashboard")
        await expect(page).to_have_url(f"{BASE}/sign-in?next=%2Fdashboard")
        print("ok  sign out")

        # 8. Facility staff confirm the request; the patient sees it confirmed.
        await sign_in(page, *STAFF)
        await expect(page.get_by_role("heading", name="Mwangaza Family Health Centre")).to_be_visible()
        await page.goto(f"{BASE}/dashboard/facility/appointments")
        row = page.locator("tr", has_text=reference)
        await row.get_by_role("button", name="Confirm").click()
        await page.get_by_label("Message to the patient").fill("Confirmed for 10:30 am.")
        await page.get_by_role("button", name="Confirm request").click()
        await expect(page.get_by_text("Request confirmed")).to_be_visible()
        await sign_out(page)
        await sign_in(page, email, "Passw0rd!")
        await page.goto(f"{BASE}/dashboard/appointments")
        await expect(page.get_by_text("Confirmed for 10:30 am.")).to_be_visible()
        print("ok  facility confirmation reaches the patient")

        # 9. Patient cannot open staff or admin areas.
        await page.goto(f"{BASE}/dashboard/admin")
        await expect(page).to_have_url(f"{BASE}/dashboard")
        print("ok  role guard")

        # 10. Contact form persists and an administrator sees it.
        await page.goto(f"{BASE}/contact")
        await page.get_by_label("Message").fill("The opening hours for a clinic in Nakuru look out of date.")
        await page.get_by_role("button", name="Send message").click()
        await expect(page.get_by_role("heading", name="Message received")).to_be_visible()
        msg_ref = await page.locator(".confirmation strong").first.inner_text()
        await sign_out(page)
        await sign_in(page, *ADMIN)
        await page.goto(f"{BASE}/dashboard/admin/messages")
        await expect(page.get_by_text(msg_ref)).to_be_visible()
        print("ok  contact message reaches administrators")

        await browser.close()
    if errors:
        print("Page errors:", *errors, sep="\n  ")
        sys.exit(1)
    print("All browser journeys passed.")


if __name__ == "__main__":
    if not (STAFF[1] and ADMIN[1]):
        sys.exit("Set SMOKE_STAFF_PASSWORD and SMOKE_ADMIN_PASSWORD before running the smoke test.")
    asyncio.run(main())
