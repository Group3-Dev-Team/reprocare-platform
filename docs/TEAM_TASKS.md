# Team workstreams

Use this map to identify modules and reviewers when work crosses the frontend, API and data pipeline.

| Area | Main code |
| --- | --- |
| Frontend and accessibility | `frontend/src/layouts/`, shared components and CSS |
| Accounts and permissions | Auth and account routes, user models, `useAuth`, route guards and account settings |
| Directory and maps | Facility, practitioner and reference routes, discovery pages, comparison and map components |
| Community and content | Programme, article and contact routes, library, assistant and registrations |
| Backend and database | Database session and migrations, shared models, appointments and facility workspace |
| Imports and verification | `browser_bot/`, import routes and services, backend, frontend and browser tests |

Changes to shared entry points such as `App.jsx`, `api.js` and `app/main.py` may need reviewers from more than one area.
Update the relevant contract or deployment guide when a change affects another workstream.
