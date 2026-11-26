# Data bot

`reprocare_bot.py` is the entry point for collecting, staging and importing public facility information and feedback.
From the repository root, run `backend/.venv/bin/python browser_bot/reprocare_bot.py --help` to see the commands. The bot stages feedback under
`REPROCARE_BOT_HOME` and can import it directly into PostgreSQL or through the authenticated
`POST /api/import/external-feedback` API. The separate facility directory endpoint is `POST /api/import/facilities`.

Keep browser profiles, credentials, caches and staged data outside Git. See the [pipeline guide](../docs/BOT_PIPELINE.md)
for platform behaviour and the [import contract](../docs/DATA_IMPORT_CONTRACT.md) for API payloads.
