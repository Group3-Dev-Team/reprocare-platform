# ReproCare: shared project foundation

ReproCare is a reproductive healthcare discovery platform for Kenya. This foundation contains the structure, configuration,
shared code and conventions every workstream builds on. Feature code (discovery, appointments, reviews, programmes,
public feedback, administration) is added in feature branches on top of it.

## What this foundation contains

**Working now:** the FastAPI app with a health endpoint, settings, database session, table creation, migration runner,
test-database guard, session-token authentication helpers and role checks (`require_role`), shared models (users,
sessions, notifications, facilities with services/insurers/lab tests, practitioners, data sources and import batches),
the reference catalogue seed (`python -m app.database.seed_reference`), and test factories (`make_user`,
`make_facility`). The React app has the real header, footer, theme switch, dashboard shell, API client, session
handling, design tokens and the shared UI kit (forms, modal, badges, pagination, toasts, feedback states).

**Placeholders for workstreams:** the empty files already in the repository (for example
`frontend/src/pages/FindCarePage.jsx`, `backend/app/routes/appointment_routes.py`) mark where each workstream's code
goes. Nothing imports them yet. Navigation links to features that are not merged show the not-found page, and the
dashboard shows a placeholder until patient, facility and admin pages are added.

The complete application (shared as a ZIP) uses exactly this structure, so code can move across file by file.
See `docs/TEAM_TASKS.md` for workstream ownership.

## Layout

| Path | Contents |
| --- | --- |
| `frontend/` | React 18 + Vite 7 single-page app. `src/services/api.js` (HTTP client), `src/hooks/` (auth session, data fetching, theme, page metadata), `src/components/` (shared UI primitives), `src/styles/` (design tokens, base, components, layout, dark theme), `src/layouts/` and `src/App.jsx` (router shell). |
| `backend/` | FastAPI + SQLAlchemy 2 + PostgreSQL. `app/config.py` (settings), `app/database/` (session, table creation, migration runner, test-database guard), `app/models/` (users, sessions, notifications, facilities and reference data), `app/services/` (auth/session helpers, pagination, county names), `app/main.py` (app factory and router registration). |
| `backend/migrations/` | Additive, numbered migrations. See its README for conventions. |
| `browser_bot/` | Standalone data collection bot: configuration and the import contract. |
| `database/` | Schema reference (`schema.sql`, `schema.dbml`). |
| `docs/` | Architecture, database, import contract, routes and roles, conventions, deployment, data coverage. |

## Requirements

Node.js 20+ (npm 9+), Python 3.12+, PostgreSQL 14+.

## Setup

```bash
# Backend
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # then set DATABASE_URL and CORS_ORIGINS
.venv/bin/python -m app.database.migrate
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm ci
cp .env.example .env.local      # VITE_API_URL=http://localhost:8000
npm run dev                     # http://localhost:5173
```

`GET /api/health` returns `{"status": "ok"}` and the home page shows whether the API is reachable.

## Tests

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/reprocare_test .venv/bin/python -m pytest
cd frontend && npm test
```

The session-wide `database` fixture drops and rebuilds every table in `TEST_DATABASE_URL` and loads the reference
catalogue. Use the `make_user` and `make_facility` fixtures instead of other workstreams' endpoints or demo data. The guard in
`app/database/test_safety.py` refuses any database whose name does not contain `test` or `scratch`, or that matches
`DATABASE_URL` in `backend/.env`.

## Adding a feature

* Backend: add `app/models/<feature>.py` (export it from `app/models/__init__.py`), `app/schemas/<feature>.py`,
  `app/services/<feature>_service.py` and `app/routes/<feature>_routes.py` with a `router`, then add the module to
  `ROUTERS` in `app/main.py`. Add a migration for any new table or column, and tests under `backend/tests/`.
* Frontend: add the page under `src/pages/`, lazy-load it in `src/App.jsx`, and add API calls to `src/services/api.js`.
  Use the design tokens in `src/styles/tokens.css`; do not hard-code colours.
* Shared files (`App.jsx`, `api.js`, `tokens.css`, `main.py`, `models/__init__.py`) change in small, separate pull
  requests that say what they add.

## Configuration and security

Real values live only in `backend/.env` and `frontend/.env.local`, which Git ignores. Anything prefixed `VITE_` is
public in the browser bundle. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
