# Database

ReproCare uses PostgreSQL and SQLAlchemy 2. The models in `backend/app/models/` and migrations in `backend/migrations/versions/` describe the current schema. `database/schema.sql` and `database/schema.dbml` are reference snapshots for diagrams.

## Import into DrawSQL

1. In DrawSQL create a diagram with the **PostgreSQL** database type.
2. Choose *Import* → *SQL* and paste the contents of `database/schema.sql`.
3. Tables, columns, primary keys, foreign keys and unique constraints appear; arrange them by area (below).

`schema.dbml` can also be imported into dbdiagram.io.

## Core tables by area

| Area | Tables |
| --- | --- |
| Accounts | `users`, `user_sessions`, `notifications`, `password_resets`, `google_identities`, `google_authorizations`, `google_link_authorizations` |
| Directory | `facilities`, `services`, `facility_services`, `insurers`, `facility_insurers`, `lab_tests`, `practitioners` |
| Patient activity | `appointment_requests`, `saved_facilities`, `reviews` |
| Community | `community_programs`, `program_registrations` |
| Content | `articles`, `contact_messages` |
| Provenance | `data_sources`, `import_batches` |

## Main relationships

* **Facility ↔ Service** and **Facility ↔ Insurer** are many-to-many through `facility_services` and `facility_insurers` (composite primary keys).
* **Facility → LabTest** one-to-many (cascade delete). **Practitioner → Facility** many-to-one (nullable; set null if the facility is removed).
* **User (facility_staff) → Facility** many-to-one. A check constraint enforces that `facility_id` is set *only* for facility staff.
* **AppointmentRequest** belongs to one patient (`user_id`) and one facility, optionally one service and one practitioner. Status is limited to `requested | confirmed | declined | cancelled`.
* **Review** belongs to one facility and (optionally) its author; `status` is `pending | published | rejected`; rating 1–5 by check constraint. ReproCare review ratings are computed from this table.
* **SavedFacility** is the join of user and facility (composite primary key, so saving twice is impossible).
* **ProgramRegistration** joins a user to a community programme; `UNIQUE (program_id, user_id)` stops double registration; capacity is checked in the API with a row lock.
* **Facility → DataSource** says where a record came from; `UNIQUE (source_id, external_id)` is the stable identifier the import uses to update instead of duplicate. Every import writes an **ImportBatch**.
* **Notification** and **UserSession** belong to a user and are deleted with it.

## Indexes and constraints worth knowing

* Unique: `users.email`, every `slug`, every `reference`, `user_sessions.token_hash`, `data_sources.code`.
* Indexed for search: `facilities.town`, `.county`, `.facility_type`, `.name`, `.is_demo`; `practitioners.specialty`, `.town`; `community_programs.start_date`, `.town`, `.cost_type`.
* Check constraints list allowed values for roles, facility types, registration status, appointment/registration/review/programme status, contact topics and rating range.

## Demonstration data

The frontend preview has an in-browser demo dataset. Backend tests create fixture rows in a disposable PostgreSQL database. The facility directory labels stored rows with `is_demo = true`. See the [import contract](DATA_IMPORT_CONTRACT.md) for fixture behaviour.

## External public feedback

ReproCare patient scores use `reviews`. Directory filters and sorting can separately use stored Google ratings and visible public activity.

* `facility_external_profiles` — a facility's Google place / Facebook page / TikTok search; Google's own `rating`, `rating_count`, photo references; unique (facility, platform, external_id).
* `external_posts` — Facebook post, TikTok video or Google listing; unique (platform, external_id); `facility_id`, `match_method`, caption, thumbnail, dates.
* `external_comments` — comment / reply (`parent_id`) / Google review (`source_rating`, Google's stars); unique (platform, external_id); visibility status, screening reasons and moderation information.
* `external_collection_runs` — log of every bot step and its outcome.
* `schema_migrations` — versions applied by `python -m app.database.migrate`.

Migration `0002_migrate_integration_feedback` copies the earlier integration build's `external_feedback` / `external_google_ratings` rows into these tables and leaves the originals untouched.
