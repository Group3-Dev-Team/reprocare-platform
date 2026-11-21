# Conventions

Short rules so that six people can work in the same repository without stepping on each other.

## Folders: what goes where

| Folder | Put here | Do not put here |
| --- | --- | --- |
| `backend/app/routes/` | HTTP endpoints for one area (`<area>_routes.py`) | SQL that other routes also need → `services/` |
| `backend/app/services/` | Logic reused by several routes, external API clients | Request/response parsing |
| `backend/app/models/` | SQLAlchemy tables, grouped by area | Business rules |
| `backend/app/schemas/` | Pydantic request bodies | Database access |
| `backend/app/database/` | Engine/session, table creation, seed, schema export | Endpoint code |
| `frontend/src/pages/` | One component per route (`<Name>Page.jsx`; dashboard pages in `pages/dashboard/`) | Components reused by other pages |
| `frontend/src/components/` | Reusable UI (`FacilityCard.jsx`, `Modal.jsx`) | Data fetching for a whole page |
| `frontend/src/services/api.js` | Every HTTP call | Anything visual |
| `frontend/src/hooks/` | `use…` functions and context providers | Components |
| `frontend/src/data/` | Static lists: navigation, labels, assistant content | Data that belongs in the database |
| `frontend/src/styles/` | CSS by layer (tokens, components, layout, pages, dashboard) | Inline colour values |

## Naming

* **Python**: `snake_case` files, functions and variables; `PascalCase` classes; route files end in `_routes.py`, services in `_service.py`.
* **Database**: plural `snake_case` table names (`appointment_requests`); foreign keys `<thing>_id`; booleans read as questions (`is_demo`, `accepts_appointment_requests`); check constraints `ck_<table>_<rule>`.
* **API paths**: lower-case, plural nouns, hyphens (`/api/lab-tests`). The signed-in user's own records live under `/api/me/…`, facility staff under `/api/facility/…`, administrators under `/api/admin/…`. Public records are addressed by `slug`, private ones by `reference` (e.g. `APT-7K3Q9X`).
* **React**: `PascalCase.jsx` for components, `camelCase.js` for other modules; hooks start with `use`; event handlers are verbs (`save`, `cancel`, `respond`).
* **CSS**: lower-case hyphenated classes named after the thing (`.facility-card`, `.facility-foot`), not the look (`.blue-box`). Modifier states use `is-` (`.is-open`, `.is-selected`).
* **Frontend routes**: lower-case and hyphenated; nested under the menu they belong to (`/find-care/laboratories`, `/health-community/free-care`).

## Code

* Validate input with Pydantic, not by hand in the route.
* Enforce ownership in the query (`WHERE user_id = :me`), never only in the frontend.
* Never return passwords, token hashes or other users' private data.
* Write user-facing messages in plain, specific English: what happened and what to do next ("This programme is full."), never "Error 409".
* Use design tokens (`var(--blue-600)`) instead of raw colours. Use the shared components (`Button` classes, `Field`, `Modal`, `EmptyState`) before writing new ones.
* Every page handles four states: loading, error, empty and success.
* Keep demo data clearly marked: any fictional record has `is_demo = true` and shows the "Demonstration record" label.
* Imports: standard library, then third-party, then `app.` (Python); React and libraries first, then local files (JS).
* Formatting: 4-space Python (PEP 8, ~140 columns); 2-space JS/JSX/CSS with single quotes.

## Git workflow

1. Branch from `main`: `feature/<jira-key>-short-name` (e.g. `feature/RC-42-lab-filters`) or `fix/<jira-key>-…`.
2. Keep changes inside your workstream's files (see `TEAM_TASKS.md`). If you must change a shared file (`App.jsx`, `api.js`, `main.py`, `tokens.css`), say so in the pull request.
3. Before opening a pull request: `pytest` (backend), `npm test && npm run build` (frontend).
4. One reviewer from another workstream approves. Do not delete a failing test to make a build pass.
5. If you change a model, run `python -m app.database.export_schema` and commit the updated `database/` files in the same pull request.
