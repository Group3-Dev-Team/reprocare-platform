# Routes and roles

## Roles

| Role | Created by | Can do |
| --- | --- | --- |
| Visitor (not signed in) | — | Search, filter, compare, map, read facility/practitioner/programme pages, library, assistant, patient experiences, contact form |
| `patient` | Self-registration | Everything a visitor can, plus save facilities, send/cancel appointment requests, register/cancel programme places, write reviews, notifications, account settings |
| `facility_staff` | Administrator | For **their own facility only**: answer appointment requests, edit the public profile fields, reply to reviews; notifications, account settings |
| `admin` | Administrator | Moderate reviews, manage community programmes and see registrations, handle contact messages, create staff accounts and (de)activate accounts, run and review data imports |

Roles from v0.8.1 that existed only for the commercial model — *business partner (organization)* and *platform owner* — were removed. *Private practitioner* accounts were removed with the provider onboarding pages; practitioners remain as directory listings.

## Public pages

| Path | Page |
| --- | --- |
| `/` | Home |
| `/find-care/facilities` | Hospitals & clinics (search, filters, list/map, 40 per page) |
| `/find-care/specialists`, `/find-care/specialists/:slug` | Practitioner directory and profile |
| `/find-care/laboratories` | Laboratory test search and laboratory list |
| `/find-care/insurance` | Facility search starting from an insurer |
| `/find-care/map` | Map-first facility search (click map to search nearby) |
| `/find-care/google` | Live Google Places search (needs configuration) |
| `/facilities/:slug` | Facility detail |
| `/compare` | Side-by-side comparison (up to three) |
| `/health-community/free-care` | Free and subsidised programmes |
| `/health-community/programmes`, `/programmes/:slug` | Community programmes and detail |
| `/health-library`, `/health-library/:slug` | Health library and article |
| `/assistant` | Health assistant (English/Kiswahili) |
| `/patient-experiences` | Moderated reviews across facilities |
| `/about`, `/how-it-works`, `/trust`, `/contact` | Informational pages |
| `/privacy`, `/terms` | Legal drafts |
| `/sign-in`, `/register` | Authentication |

## Signed-in pages

| Path | Role |
| --- | --- |
| `/dashboard`, `/dashboard/appointments`, `/dashboard/saved`, `/dashboard/registrations`, `/dashboard/reviews` | patient |
| `/dashboard/facility`, `/dashboard/facility/appointments`, `/dashboard/facility/profile`, `/dashboard/facility/reviews` | facility_staff |
| `/dashboard/admin`, `/dashboard/admin/reviews`, `/dashboard/admin/programmes`, `/dashboard/admin/messages`, `/dashboard/admin/users`, `/dashboard/admin/imports` | admin |
| `/dashboard/notifications`, `/dashboard/account` | any signed-in role |

A signed-out visitor is sent to `/sign-in?next=…`; a signed-in user opening another role's area is sent to their own dashboard.

## API endpoints (all under `/api`)

| Method and path | Access | Purpose |
| --- | --- | --- |
| GET `/health`, `/stats`, `/services`, `/insurers`, `/towns` | public | Health check and reference lists |
| POST `/auth/register`, `/auth/login` | public | Create patient account / sign in (returns token) |
| POST `/auth/logout`; GET, PATCH `/auth/me`; POST `/auth/change-password` | signed in | Session and own profile |
| GET `/facilities`, `/facilities/markers`, `/facilities/{slug}`, `/facilities/{slug}/reviews` | public | Search (filters: q, town, county, facility_type, service, insurer, open_weekends, open_24_hours, telehealth, accepts_requests, verified_only, hide_demo, exclude_laboratories, lat, lng, radius_km, sort, page, page_size≤40) |
| POST `/facilities/{slug}/reviews` | patient | Submit a review (pending moderation) |
| GET `/reviews`, `/lab-tests`, `/practitioners`, `/practitioners/specialties`, `/practitioners/{slug}` | public | Directories |
| GET `/programs`, `/programs/{slug}`; GET `/articles`, `/articles/{slug}`; POST `/contact` | public | Programmes, library, contact form |
| POST `/appointments`; GET `/me/appointments`; POST `/me/appointments/{ref}/cancel` | patient | Appointment requests |
| GET `/me/saved`; PUT, DELETE `/me/saved/{slug}` | patient | Saved facilities |
| POST `/programs/{slug}/registrations`; GET `/me/registrations`; POST `/me/registrations/{ref}/cancel` | patient | Programme registrations |
| GET `/me/reviews` | patient | Own reviews and moderation status |
| GET `/me/notifications`; POST `/me/notifications/read` | signed in | Notifications |
| GET `/facility/overview`, `/facility/appointments`, `/facility/reviews`; PATCH `/facility/appointments/{ref}`, `/facility/profile`; PUT `/facility/reviews/{id}/reply` | facility_staff (own facility) | Facility workspace |
| GET `/admin/overview`, `/admin/reviews`, `/admin/users`, `/admin/contact-messages`, `/admin/programs`, `/admin/programs/{slug}/registrations`, `/admin/imports` | admin | Operations |
| POST `/admin/reviews/{id}/moderate`, `/admin/users`, `/admin/programs`; PATCH `/admin/users/{id}`, `/admin/contact-messages/{ref}`, `/admin/programs/{slug}` | admin | Operations |
| POST `/import/facilities` | admin session or `X-Import-Key` | Bot ingestion |
| GET `/places/status`, `/places/search` | public | Live Google Places (503 if not configured) |

Interactive documentation with request/response examples: `http://localhost:8000/docs` (disabled in production).

## Added in v2.1 — external public feedback

| Method | Path | Who |
| --- | --- | --- |
| GET | `/api/facilities/{slug}/public-feedback` | Public |
| GET | `/api/facilities/{slug}/public-feedback/posts` | Public (paginated, `page_size` ≤ 20) |
| GET | `/api/external-posts/{id}/comments` | Public (paginated, `page_size` ≤ 40) |
| GET | `/api/counties` | Public (47 counties with facility counts) |
| POST | `/api/import/external-feedback` | Bot (`X-Import-Key`) or admin |

No administration pages or endpoints were added for public feedback in this phase. The facility page gains a "Public feedback" section and a section navigation.
