# ReproCare

ReproCare helps people in Kenya find reproductive healthcare and decide where to go, using facility information and
genuine public feedback about each facility.

## What it does

- **Find care**: search the facility directory by name, service, county, town, insurer, facility type, opening hours
  and review availability, in list, grid or map view. Sort by relevance, completeness, name, Google Maps rating or
  ReproCare patient rating, or show only facilities with public reviews.
- **Live Google Maps search**: find places that are not yet in the directory. Live results show their Google rating, are
  labelled as live and unstored, and open a live listing with written Google reviews on request. Places already in the
  directory link to their listing instead.
- **Facility pages**: services, hours, contacts, map, Google Maps ratings and written reviews (loaded live when asked
  for), approved Facebook and TikTok comments, ReproCare patient reviews, comparisons and saved facilities.
- **Appointments**: patients send appointment requests to participating facilities; providers confirm, decline or
  reschedule them. For other facilities, Book appointment shows the facility's own contact options.
- **Accounts and dashboards**: patient, provider and administrator dashboards; email sign-in, optional Google sign-in
  and password recovery by email.
- **Health information**: articles, programmes, community resources, care planning, visit preparation and health
  alerts, with clinical review notices.
- **Public feedback pipeline**: a local bot collects public Facebook comments (Playwright, signed-in browser on the
  operator's machine) and TikTok comments (Apify). Screening holds sensitive material. Facebook comments wait for
  moderation unless optional screening is enabled and approves them. Instagram is limited to offline captures.

## Architecture

```
React (Vite) static site  →  FastAPI backend  →  PostgreSQL (Supabase in the shared deployment)
                                    ↘ Google Places API (server-side key; live, not stored)
Local bot (Playwright, Apify) → screening → admin review → approved feedback in the database
```

- `frontend/`: React 18 + Vite single-page app.
- `backend/`: FastAPI, SQLAlchemy 2, additive SQL migrations in `backend/migrations/versions/`.
- `browser_bot/`: Facebook and TikTok collectors, screening and import staging.
- `database/`: schema reference. `docs/`: architecture, database, routes and roles, data import, deployment.

The hosted backend connects to Supabase with a restricted application login. The optional private bot can use the
import API or a configured database login. Website users need no database credentials or API keys.

Live Google results show Google's attribution and have per-visitor and daily request limits. The directory can
also show rating snapshots from earlier collection. Written Google reviews are fetched when requested.

## Local setup

Use Node.js 22 (22.22.2 or later) for the frontend build and tests. The backend uses Python 3.12 and PostgreSQL 14+.

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                 # set DATABASE_URL and CORS_ORIGINS
.venv/bin/python -m app.check_config # reports missing settings without printing secrets
.venv/bin/python -m app.database.migrate
.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend
npm ci
cp .env.example .env.local           # VITE_API_URL=http://localhost:8000
npm run dev                          # http://localhost:5173
```

Optional settings stay off until configured: `GOOGLE_PLACES_API_KEY` (live Google search, ratings and reviews),
`GOOGLE_PLACES_PHOTO_DAILY_LIMIT` (Google photos; 0 = off), `PASSWORD_RESET_*` (SMTP or an HTTPS email API),
`GOOGLE_OAUTH_*` (Google sign-in) and `APIFY_API_TOKEN` (TikTok collection). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
Real values belong only in `backend/.env` and `frontend/.env.local`, which Git ignores. `VITE_` values are public.

## Tests

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/reprocare_test .venv/bin/python -m pytest
cd backend && TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/reprocare_bot_test .venv/bin/python -m pytest ../browser_bot/tests
cd frontend && npx vitest run --maxWorkers=2
```

Use dedicated local PostgreSQL databases for backend and bot tests. The backend fixture rebuilds every table in
`TEST_DATABASE_URL`. The guard checks the database name and refuses a target that matches the database in
`backend/.env`. Tests use fixtures and mocked external services.

## Deployment

The frontend runs as a Render static site and the backend as a Render web service, using the existing Supabase
PostgreSQL database. Steps and variables are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Current limitations

- The directory includes historical Ministry of Health registry records, OpenStreetMap entries and facility-page
  listings. Source labels indicate provenance. Confirm current operations and availability directly with the facility.
- Public reviews lists facilities with approved Facebook or TikTok comments or a stored Google rating. Live Google
  ratings appear on live results and listings but are not used to filter the whole directory, because that would need
  one Google request per facility.
- Facebook and TikTok comments are presented as public feedback. TikTok collection has been tested offline only.
- Google photos are off unless a daily photo limit is set. Facilities without a genuine photo keep their type icon.
