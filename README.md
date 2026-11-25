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
  operator's machine) and TikTok comments (Apify). Comments are screened for personal health details and reviewed by
  an administrator; only approved comments are published. Instagram collection is disabled.

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

The hosted backend is the only component with database access. It connects to Supabase with a restricted application
login. Team members and visitors use the website and need no database credentials or API keys.

Google content (ratings, reviews, photos) is fetched live for display with Google's attribution and is not stored,
apart from Place IDs. Live requests have per-visitor and daily limits on the server.

## Local setup

Requirements: Node.js 20+, Python 3.12, PostgreSQL 14+.

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
cd backend && TEST_DATABASE_URL=... .venv/bin/python -m pytest ../browser_bot/tests
cd frontend && npx vitest run --maxWorkers=2
```

The backend test fixture rebuilds every table in `TEST_DATABASE_URL`. A guard refuses any database whose name lacks
`test` or `scratch`, or that matches `DATABASE_URL`. Tests use fixtures and mocked external services and make no
network requests.

## Deployment

The frontend runs as a Render static site and the backend as a Render web service, using the existing Supabase
PostgreSQL database. Steps and variables are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Current limitations

- The shared directory holds OpenStreetMap facilities. Facilities from earlier Google-based collection that have no
  confirmed directory match are found through live Google search until independent directory records are added.
- Public reviews lists facilities with approved Facebook or TikTok comments or a stored Google rating. Live Google
  ratings appear on live results and listings but are not used to filter the whole directory, because that would need
  one Google request per facility.
- Facebook and TikTok feedback appears only after collection and administrator approval. TikTok collection has been
  tested offline only.
- Google photos are off unless a daily photo limit is set. Facilities without a genuine photo keep their type icon.
