# Migrations

* Files in `versions/` are applied once, in name order, by `python -m app.database.migrate` and recorded in `schema_migrations`.
* Name them `NNNN_short_description.sql` (run as-is) or `.py` (defines `upgrade(db)`). Take the next free number when the pull request is opened; if two branches collide, the later one renumbers before merging.
* Migrations are additive: create tables, add nullable columns or indexes. Never drop or rewrite data in a migration.
* Model changes and their migration go in the same pull request. `create_all` builds fresh databases from the models, so the model must match the migrated schema.
* Rehearse on a disposable copy before applying to a shared database. Even `migrate --status` creates missing tables.
* Give the test suite its own disposable database. The tests reset `TEST_DATABASE_URL`.
