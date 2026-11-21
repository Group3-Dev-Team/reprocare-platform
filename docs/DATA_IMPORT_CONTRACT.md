# Data import contract (for the independent ReproCare data bot)

The bot runs outside this repository. It discovers facilities from permitted public sources, then sends structured records to ReproCare. ReproCare validates, de-duplicates and stores them. The main application works whether or not the bot is running.

## Endpoint

```
POST /api/import/facilities
Content-Type: application/json
X-Import-Key: <value of IMPORT_API_KEY in backend/.env>
```

A signed-in administrator can call the same endpoint (the *Data imports* page does this). Without a valid key or admin session the API returns **401**.

## Request body

```json
{
  "source": { "code": "reprocare_bot", "name": "ReproCare data bot", "attribution": "Collected from the KMHFL public export" },
  "is_demo": false,
  "facilities": [
    {
      "external_id": "kmhfl-12345",
      "name": "Example Health Centre",
      "facility_type": "health_centre",
      "town": "Nakuru",
      "county": "Nakuru",
      "address": "Kenyatta Avenue",
      "area": "Town centre",
      "latitude": -0.2950,
      "longitude": 36.0700,
      "phone": "+254700000000",
      "email": "",
      "website": "",
      "description": "",
      "weekday_hours": "8:00 am – 5:00 pm",
      "saturday_hours": "9:00 am – 1:00 pm",
      "sunday_hours": "Closed",
      "open_24_hours": false,
      "services": ["antenatal", "contraception"],
      "insurers": ["sha"],
      "registration": { "status": "matched", "body": "Kenya Master Health Facility List", "code": "12345", "checked_on": "2026-11-10" }
    }
  ]
}
```

| Field | Rules |
| --- | --- |
| `source.code` | Required. 2–40 chars, `a-z 0-9 _`. Created on first use. `demo` is reserved. |
| `is_demo` | `true` for test fixtures. Their records are labelled "Demonstration record" and kept apart from genuine listings. |
| `facilities` | 1–500 records per request. |
| `external_id` | Required. The source's stable identifier (registry code, Google place ID…). |
| `name`, `town`, `county` | Required. |
| `facility_type` | Required. One of `hospital`, `clinic`, `maternity_home`, `health_centre`, `laboratory`. |
| `latitude`, `longitude` | Optional. Must fall inside Kenya's bounding box (lat −5.0 to 5.5, lng 33.5 to 42.5). |
| `services` | Optional list of service slugs from `GET /api/services`. Unknown slugs reject the record. Omit the field to keep a facility's existing service links; send `[]` to clear them. |
| `insurers` | Optional list of insurer slugs from `GET /api/insurers`. Unknown slugs reject the record. Omit the field to keep existing insurer links; send `[]` to clear them. |
| `registration.status` | `matched`, `not_checked` (default) or `unresolved`. |

## Behaviour

* Each record is validated on its own. Invalid records are reported and skipped; valid ones are saved.
* `(source.code, external_id)` identifies a record. Sending it again **updates** the existing facility instead of creating a duplicate.
* A new record whose name and town match an existing facility from another source is saved and reported under `warnings` as a possible duplicate for an administrator to review.
* Every call is logged in `import_batches` and visible on the admin *Data imports* page.
* Only send data the source permits you to store. Google Places content (other than place IDs) must not be sent here; use the live search page instead.

## Response

```json
{
  "batch_id": 3, "source": "reprocare_bot",
  "received": 3, "created": 2, "updated": 0, "failed": 1,
  "errors":   [{ "index": 2, "external_id": "fixture-0003", "error": "facility_type: Input should be 'hospital', 'clinic', ..." }],
  "warnings": [],
  "records":  [{ "external_id": "fixture-0001", "slug": "fixture-riverside-clinic-nakuru" }]
}
```

Imported facilities are immediately searchable through `GET /api/facilities` and viewable at `GET /api/facilities/{slug}`.

## Try it

```bash
curl -X POST http://localhost:8000/api/import/facilities \
  -H "Content-Type: application/json" -H "X-Import-Key: $IMPORT_API_KEY" \
  -d @backend/tests/sample_import.json
```

`backend/tests/test_import.py` submits that sample, checks that two records are created and one rejected, re-sends it to prove updates do not duplicate, and fetches the result through the public API.

## External public feedback (v2.1)

`POST /api/import/external-feedback` with `X-Import-Key`. Body: `{"batches": [ ... ]}` (≤200), each batch:

```json
{
  "platform": "facebook | tiktok | google",
  "facility_slug": "kenyatta-national-hospital",
  "google_place_id": null,
  "post": {"external_id": "…", "url": "https://web.facebook.com/<page>/posts/…", "author_name": "", "caption": "", "thumbnail_url": "", "published_at": null, "collected_at": null, "match_method": "facility_page_post"},
  "comments": [{"external_id": "…", "parent_external_id": null, "author_name": "", "author_is_facility": false, "text": "…", "published_at": null, "published_at_approximate": false, "like_count": null, "source_rating": null}]
}
```

Rules: facility by slug or Google place id only; the URL must belong to the platform; a post is never moved to another facility; existing posts/comments are skipped; each batch is accepted or rejected as a whole. Response: `received, imported, comments_created, comments_skipped, errors[]`.
