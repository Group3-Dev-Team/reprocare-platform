# Team workstreams (for Jira)

Six workstreams map onto the code so each developer mostly edits their own files. **Shared files** (`frontend/src/App.jsx`, `frontend/src/services/api.js`, `frontend/src/styles/tokens.css`, `backend/app/main.py`, `backend/app/models/__init__.py`) are changed in small pull requests that mention the change; the Scrum Master assigns one owner for each.

Suggested Jira setup: one **Epic** per workstream, stories prefixed with the epic key (RC-UI, RC-AUTH, RC-FIND, RC-COMM, RC-API, RC-DATA).

## 1. Frontend UI, design system and responsive layouts (RC-UI)

* **Owns**: `frontend/src/styles/*`, `components/{Header,Footer,Sidebar,Logo,PageHeader,Modal,Forms,Feedback,Pagination,Badges,Toast,ErrorBoundary,DemoBanner,CompareBar}.jsx`, `layouts/*`, `pages/{HomePage,AboutPage,HowItWorksPage,TrustPage,ContactPage,LegalPages,NotFoundPage}.jsx`, `data/navigation.js`, `data/images.js`.
* **Depends on**: nothing; other streams use its components.
* **Starter stories**: replace illustrative photographs with licensed Kenyan healthcare imagery (see `frontend/src/data/images.js`); add print styles for facility pages; audit colour contrast with axe; add a skip-to-filters link on search pages.
* **Done when**: every page passes keyboard-only navigation, has no horizontal scroll at 360 px, and uses only design tokens.

## 2. Authentication, accounts and role dashboards (RC-AUTH)

* **Owns**: `backend/app/routes/{auth_routes,account_routes,admin_routes}.py`, `services/auth_service.py`, `schemas/{auth,admin}.py`, `models/user.py`; `frontend/src/hooks/useAuth.jsx`, `components/ProtectedRoute.jsx`, `pages/{SignInPage,RegisterPage}.jsx`, `pages/dashboard/{PatientOverview,Notifications,AccountSettings,AdminOverview,AdminUsers,AdminMessages}.jsx`.
* **Depends on**: RC-API for models.
* **Starter stories**: activate password recovery once an approved SMTP sender exists; activate Google sign-in with approved credentials; staff invitation and revocation flow; expire old sessions with a cleanup command.
* **Done when**: `tests/test_auth.py` and `tests/test_permissions.py` cover the new rule; no endpoint returns another user's private data.

## 3. Facilities, practitioners, discovery, search and map (RC-FIND)

* **Owns**: `backend/app/routes/{facility_routes,practitioner_routes,reference_routes,places_routes}.py`, `services/{facility_service,google_places_service}.py`, `models/{facility,practitioner}.py`; `frontend/src/pages/{FindCarePage,FacilityDetailPage,SpecialistsPage,PractitionerDetailPage,LaboratoriesPage,ComparePage,GooglePlacesPage}.jsx`, `components/{FacilityCard,PractitionerCard,MapView,GooglePlacesMap,SaveButton}.jsx`, `hooks/{useSaved,useCompare}.jsx`.
* **Depends on**: RC-UI components, RC-API.
* **Starter stories**: marker clustering on the map; "open now" filter using structured hours; accessibility filters; practitioner–facility many-to-many.
* **Done when**: `tests/test_discovery.py` covers each new filter against real data and the empty state still appears for impossible combinations.

## 4. Health education, community programmes and registration (RC-COMM)

* **Owns**: `backend/app/routes/{program_routes,content_routes}.py`, `models/{program,content}.py`, `schemas/{program,contact}.py`; `frontend/src/pages/{ProgramsPage,ProgramDetailPage,LibraryPage,ArticlePage,AssistantPage,ExperiencesPage}.jsx`, `pages/dashboard/{MyRegistrations,AdminPrograms}.jsx`, `components/{ProgramCard,RegistrationModal,ReviewCard,ReviewForm}.jsx`, `data/assistantContent.js`.
* **Depends on**: RC-UI, RC-AUTH.
* **Starter stories**: organiser check-in (mark `attended`); waiting list when full; article editor for administrators; get every article reviewed by a clinician and record the reviewer.
* **Done when**: registrations persist after refresh, capacity can never be exceeded, and article pages show their sources.

## 5. Backend APIs, PostgreSQL models and integration (RC-API)

* **Owns**: `backend/app/main.py`, `config.py`, `database/*`, `models/__init__.py`, `services/common.py`, `routes/{appointment_routes,facility_staff_routes}.py`, `schemas/{appointment,review}.py`, `models/{appointment,review}.py`; `database/schema.sql`, `schema.dbml`; `frontend/src/services/api.js`; `pages/dashboard/{MyAppointments,SavedFacilities,MyReviews,FacilityOverview,FacilityAppointments,FacilityProfile,FacilityReviews,AdminReviews}.jsx`, `components/AppointmentModal.jsx`.
* **Depends on**: —
* **Starter stories**: versioned SQL migrations folder for production changes; appointment reminders; facility "request more information" status; deployment guide for a managed PostgreSQL.
* **Done when**: `pytest` passes on a fresh database and `export_schema` output is committed with every model change.

## 6. Data ingestion, testing and quality assurance (RC-DATA)

* **Owns**: `backend/app/routes/import_routes.py`, `services/import_service.py`, `schemas/data_import.py`, `models/data_import.py`, `backend/tests/*`, `tests/e2e_smoke.py`, `frontend/src/tests/*`, `pages/dashboard/AdminImports.jsx`, `docs/DATA_IMPORT_CONTRACT.md`; liaison with the separate `reprocare-data-bot` repository.
* **Depends on**: RC-API.
* **Starter stories**: duplicate-review queue for name/town warnings; import dry-run mode; GitHub Actions workflow running pytest, Vitest and the build on every pull request; accessibility test with axe-playwright.
* **Done when**: the bot can import a batch with only the contract document, and CI blocks merging on any failing test.
