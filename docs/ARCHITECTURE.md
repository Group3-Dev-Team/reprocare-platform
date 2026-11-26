# Architecture

ReproCare has a React single-page app, a FastAPI JSON API and a PostgreSQL database. The API enforces application permissions. The data bot runs separately.

```
 Browser (React + Vite)                 FastAPI (Python)                       PostgreSQL
 ┌──────────────────────────┐   HTTPS   ┌───────────────────────────────┐ SQL  ┌──────────────┐
 │ pages/  → services/api.js│ ───────▶ │ routes/ → services/ → models/ │ ───▶ │ App tables   │
 │ hooks/useAuth (token)    │ ◀─────── │ schemas/ validate input        │ ◀─── │              │
 └──────────────────────────┘   JSON    └───────────────┬───────────────┘      └──────────────┘
                                                        │ HTTPS (server key)
                     External data bot ── POST /api/import/facilities          Google Places API (New)
```

## Frontend

* **Routing** — `src/App.jsx` lists every route. Public pages render inside `layouts/PublicLayout.jsx` (top navigation, footer, compare bar). Signed-in areas render inside `layouts/DashboardLayout.jsx` (sidebar, top bar). Dashboard pages are lazy-loaded.
* **Data access** — pages never call `fetch` directly. `services/api.js` has one named function per endpoint (`api.facilities(params)`, `api.requestAppointment(body)`…). It adds the bearer token, turns error responses into `ApiError` (message + per-field messages), and signals a sign-out when the token is rejected.
* **Loading data** — `hooks/useFetch.js` wraps an `api` call and returns `{ data, loading, error, reload }`. Every page shows the shared `LoadingState`, `ErrorState` and `EmptyState` from `components/Feedback.jsx`.
* **App-wide state** — contexts handle authentication, saved facilities, comparisons and notifications shown in the UI. Shareable filters live in the URL query string.
* **Styling** — plain CSS. `styles/tokens.css` defines colours, type scale, spacing, radii and shadows; all other files use the variables. `components.css` holds shared components, `layout.css` the site chrome, `pages.css` page-specific styles, `dashboard.css` the signed-in workspace.
* **Maps** — `components/MapView.jsx` wraps Leaflet with OpenStreetMap tiles for ReproCare's own records (stored coordinates only). Google Places results use `components/GooglePlacesMap.jsx` because Google's terms require Google data on a Google map.
* **Preview build** — `npm run build:preview` bundles the interface into a single HTML file. The in-browser API stub answers health checks only. Use the connected build for directory results, accounts, appointments and other API-backed features.

## Backend

* `app/main.py` creates the app, configures CORS and mounts each `routes/*_routes.py` under `/api`.
* **Routes** handle HTTP: read parameters, call services or the ORM, return JSON. One file per area: `auth`, `reference` (services, insurers, towns, stats), `facility`, `practitioner`, `appointment`, `account` (saved, notifications), `program`, `content` (articles, contact), `facility_staff`, `admin`, `import`, `places`.
* **Schemas** (`app/schemas/`) are Pydantic models for request bodies. FastAPI rejects invalid input with HTTP 422 and a list of field errors before any route code runs.
* **Services** hold logic used in more than one place: `auth_service` (bcrypt hashing, sessions, `require_role`), `facility_service` (search query builder, JSON shapes), `import_service`, `google_places_service`, `common` (pagination envelope, references, notifications).
* **Models** (`app/models/`) are SQLAlchemy 2 declarative classes. `database/session.py` provides the engine, `SessionLocal` and the `get_db` dependency (one session per request).

### Response conventions

* Lists that can grow return `{ items, total, page, page_size, pages }`; `page_size` is capped at 40.
* Errors return `{ "detail": "Plain-language message" }`, or FastAPI's list of field errors for 422.
* Status codes: 200/201/204 success, 400 rule broken, 401 not signed in, 403 wrong role, 404 not found **or not yours**, 409 duplicate/conflict, 422 invalid input, 503 integration not configured.

## Authentication and authorisation

1. `POST /api/auth/login` checks the bcrypt hash and creates a row in `user_sessions` holding the **SHA-256 hash** of a random token. The raw token goes to the browser once.
2. The browser sends `Authorization: Bearer <token>`. `get_current_user` looks up the hash, checks expiry (`SESSION_DAYS`) and that the user is active.
3. `POST /api/auth/logout` deletes the session row, so the token stops working immediately.
4. `require_role("admin")` etc. guard routes. Ownership is enforced in the query itself — e.g. `WHERE reference = :ref AND user_id = :me` — so another person's record returns 404, never data.
5. Public registration always creates a `patient`. Facility staff and administrators are created by an administrator (`POST /api/admin/users`).

The frontend's `ProtectedRoute` only improves navigation; it is not a security boundary.

## Data integration boundary

* **Independent bot** → `POST /api/import/facilities` with the `X-Import-Key` header. The backend validates each record, upserts by `(source, external_id)`, reports per-record errors and logs an `import_batches` row. The app runs normally without the bot. Contract: `DATA_IMPORT_CONTRACT.md`.
* **External feedback** → `POST /api/import/external-feedback` accepts staged feedback. The local bot contains the collection and matching tools. The web application serves published feedback with source attribution.
* **Google Places** → `GET /api/places/search` calls Text Search (New) on the server. Live searches are separate from stored directory records and linked rating snapshots.

## Database migrations

SQLAlchemy models define the current schema. Add a versioned SQL or Python migration in `backend/migrations/versions/` when changing an existing table. From `backend/`, run `python -m app.database.migrate` on a disposable database first. The files under `database/` are reference snapshots.
