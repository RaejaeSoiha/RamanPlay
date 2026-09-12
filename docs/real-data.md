# Real NFL data integration

The existing Next.js/FastAPI/SQLAlchemy architecture and GameDataProvider interface are preserved. SportsDataProvider now normalizes SportsDataIO data before writing games to the database. Frontend requests read only the application API/database.

## Configuration and activation

Set SPORTSDATAIO_API_KEY in the project-root .env, restart the backend, then run `backend/.venv/bin/python scripts/update_schedule.py` from the project root. The canonical name supersedes the old NFL_DATA_API_KEY alias. A configured key selects SportsDataIO automatically; no key selects development data. DATA_PROVIDER=json remains available for explicit local feeds when no key is present. NFL_SEASON can be blank: January–February use the previous season's starting year, March–December use the current year. SPORTSDATA_TRIAL=true marks a trial/scrambled feed as development data; the default false assumes the operator configured a production feed.

The adapter uses Scores-by-Season for PRE, REG and POST and sends credentials only in an HTTP header. It normalizes all 32 canonical teams, aliases, UTC kickoffs, scores, statuses, phase and broadcaster. Missing broadcasts remain null. The DB stores PRESEASON, REGULAR or POSTSEASON; the UI displays year, phase and week. Stable ScoreID/GameID identities are preferred; otherwise a deterministic season/phase/week/team/kickoff identity is used. The composite fallback cannot reconcile a changed kickoff without a stable provider ID; official stable IDs avoid that limitation.

## Failure and refresh behavior

Invalid keys/feed permissions, rate limits, network errors, timeouts, malformed JSON, invalid records, and empty seasons produce sanitized maintenance messages. All data is validated before the import writes records. Existing real data remains available on failure. If no real data exists for the requested season, development data is served with its banner. The adapter does not silently fabricate real games or networks. Previously saved final scores are preserved when provider updates are incomplete or regress in status.

Default refresh: six-hour full sync; 15-minute game-day checks; two-minute live checks. A provider error imposes at least a 15-minute automatic retry interval. Settings are configurable through SCHEDULE_HOURS, GAME_DAY_REFRESH_SECONDS and LIVE_REFRESH_SECONDS. The request cache is isolated by season, trial flag, and hashed credential. Only one embedded scheduler/backend worker should run, as in the existing architecture.

Maintenance reports active/configured provider, provider status, last successful and attempted sync, received/created/updated counts, and safe errors. CLI exits with status 1 on failed sync and prints a useful summary. The admin endpoint retains its legacy updated count for compatibility and also supplies fetched, games_created, games_updated, errors and error fields.

## Migration and validation

The idempotent schema migration adds season_type and makes the broadcaster nullable. Existing IDs, games, sources and relationships remain intact. SQLite backs up an older database to backend/watch.db.before-real-data.db before migration; SQLite 3.35+ is required for the column change. PostgreSQL uses ALTER COLUMN DROP NOT NULL; no deployment or Docker runtime work was performed in this phase.

Validation completed:

- 135 backend tests passed, including all 50 previous tests. External HTTP is mocked; tests require no account credentials.
- 13 frontend tests passed, including all four previous tests.
- Production Next.js build and TypeScript checks passed.
- Backend restarted with the migrated existing SQLite database; frontend remained running.
- Dashboard, Today, Schedule, game detail and Favorites browser checks passed; existing Denver favorite preserved. Matchup search verified separately.
- Two CLI syncs each reported development provider, 16 fetched, 0 created, 16 updated, 0 errors. Database remains at 16 games with no duplicate identities.
- SQLite schema migration is tested against an older schema and its repeated execution.

No SportsDataIO key is configured. Therefore a live authenticated sync could not be executed, and real data is not claimed to be active. Mocked tests verify the production provider pipeline, errors, phase parsing, updates, cache, final-score preservation, null broadcasts and API banner metadata. Production feed entitlement and current upstream availability still require verification with the user's account. Trial access may contain scrambled data and must be marked accordingly.

Next step: configure a licensed SPORTSDATAIO_API_KEY locally, restart the backend, run the sync command twice, and compare one week's imported games, kickoff times and scores against the official schedule before expanding viewing-source discovery.

## Files changed

- backend/app/config.py
- backend/app/models/entities.py
- backend/app/schemas/feed.py
- backend/app/services/providers.py
- backend/app/services/sportsdata.py
- backend/app/services/normalization.py (new)
- backend/app/services/ingestion.py
- backend/app/services/sync.py (new)
- backend/app/services/jobs.py
- backend/app/database/migrations.py (new)
- backend/app/api/routes.py
- backend/app/main.py
- frontend/types/index.ts
- frontend/lib/helpers.ts
- frontend/components/Dashboard.tsx
- frontend/components/Maintenance.tsx
- scripts/maintain.py
- scripts/update_schedule.py (new)
- tests/backend/conftest.py
- tests/backend/test_real_sync.py (new)
- tests/frontend/helpers.test.ts
- .env.example and local ignored .env (canonical variable/default normalization; existing secrets preserved)
- docker-compose.yml (only the data-provider environment names/defaults)
- README.md, docs/architecture.md, docs/real-data.md, docs/validation.md

Provider contract references: [API documentation](https://sportsdata.io/developers/api-documentation/nfl), [data dictionary](https://sportsdata.io/developers/data-dictionary/nfl), [workflow guide](https://sportsdata.io/developers/workflow-guide/nfl).
