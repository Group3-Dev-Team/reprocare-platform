import csv
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from time import sleep

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select
from app.database.session import SessionLocal
from app.models import Facility

OUT = ROOT / "browser_bot" / "discovery"
HEADERS = {
    "User-Agent": "ReproCareDiscovery/1.0 (research project)",
    "Accept": "application/json, application/xml, text/xml",
}

def fetch(url, data=None, timeout=25):
    request = urllib.request.Request(
        url, data=data, headers=HEADERS,
        method="POST" if data else "GET"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()

def save_csv(filename, rows, fields):
    with (OUT / filename).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

# 1. Export the facilities already in ReproCare.
with SessionLocal() as db:
    facilities = db.scalars(
        select(Facility).where(Facility.is_demo.is_(False))
    ).all()
    existing = [
        {
            "name": f.name,
            "type": f.facility_type or "",
            "town": f.town or "",
            "slug": f.slug,
        }
        for f in facilities
    ]

save_csv(
    "existing_facilities.csv", existing,
    ["name", "type", "town", "slug"]
)
print("Existing facilities:", len(existing), flush=True)

# 2. Discover healthcare facilities from OpenStreetMap.
osm = []
query = """
[out:json][timeout:90];
area["ISO3166-1"="KE"][admin_level=2]->.kenya;
(
 nwr["amenity"~"^(hospital|clinic|doctors)$"](area.kenya);
 nwr["healthcare"~"^(hospital|clinic|centre|laboratory|doctor)$"](area.kenya);
);
out center;
"""

try:
    raw = fetch(
        "https://overpass.kumi.systems/api/interpreter",
        urllib.parse.urlencode({"data": query}).encode(),
        timeout=110
    )
    for item in json.loads(raw).get("elements", []):
        tags = item.get("tags", {})
        if not tags.get("name"):
            continue
        osm.append({
            "name": tags["name"],
            "type": tags.get("healthcare") or tags.get("amenity", ""),
            "county": tags.get("addr:county", ""),
            "website": tags.get("website", ""),
            "facebook": tags.get("contact:facebook", ""),
            "osm_id": f"{item['type']}/{item['id']}",
        })
    print("OSM facilities discovered:", len(osm), flush=True)
except Exception as exc:
    print("OSM unavailable:", type(exc).__name__, flush=True)

save_csv(
    "osm_candidates.csv", osm,
    ["name", "type", "county", "website", "facebook", "osm_id"]
)

# 3. Search for Facebook pages across Kenyan counties.
counties = [
    "Nairobi", "Kiambu", "Mombasa", "Kisumu",
    "Nakuru", "Uasin Gishu", "Machakos",
    "Kajiado", "Nyeri", "Meru", "Kakamega",
    "Kilifi", "Bungoma", "Kisii", "Kericho",
    "Embu", "Kirinyaga", "Muranga",
    "Trans Nzoia", "Homa Bay"
]

pages = {}
for county in counties:
    search = f'site:facebook.com hospital clinic "{county}" Kenya'
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({
        "q": search, "format": "rss"
    })
    try:
        root = ET.fromstring(fetch(url, timeout=18))
        found = 0
        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            parsed = urllib.parse.urlparse(link)
            if parsed.hostname not in {
                "facebook.com", "www.facebook.com",
                "web.facebook.com", "m.facebook.com"
            }:
                continue
            parts = parsed.path.strip("/").split("/")
            if len(parts) != 1 or parts[0].lower() in {
                "groups", "posts", "watch", "reel",
                "share", "pages", "login", "events"
            }:
                continue
            clean = "https://www.facebook.com/" + parts[0]
            if clean not in pages:
                pages[clean] = {
                    "page_title": title,
                    "facebook_url": clean,
                    "search_county": county
                }
                found += 1
        print(f"{county}: {found} new Facebook candidates", flush=True)
    except Exception as exc:
        print(county, "search unavailable:", type(exc).__name__, flush=True)
    sleep(1)

save_csv(
    "facebook_candidates.csv", list(pages.values()),
    ["page_title", "facebook_url", "search_county"]
)

print("\n=== DISCOVERY SUMMARY ===")
print("Existing facilities:", len(existing))
print("OSM candidates:", len(osm))
print("Facebook page candidates:", len(pages))
print("Files saved in:", OUT)
print("No database records modified.")
