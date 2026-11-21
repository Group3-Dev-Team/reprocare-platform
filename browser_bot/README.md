# Data bot

The bot runs separately from the web application. It collects public facility data, stages it outside the repository
(`REPROCARE_BOT_HOME`) and imports it either directly into PostgreSQL or through the authenticated import API
(`POST /api/import/facilities` with `X-Import-Key`). The record format is defined in
[`docs/DATA_IMPORT_CONTRACT.md`](../docs/DATA_IMPORT_CONTRACT.md).

`bot_config.py` holds the shared paths, limits and credentials lookup. Collectors, staging and the importer are added by
the data-bot workstream. Keep browser profiles, sessions, caches and staged data outside Git.
