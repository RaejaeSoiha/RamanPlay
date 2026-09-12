# [RamanPlay](https://github.com/RaejaeSoiha/RamanPlay)

**All Your Games. One Place.**

RamanPlay is a personal sports game dashboard built with Next.js, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy and SQLite. NFL is its first fully supported league. Find games, inspect official viewing options, follow teams, search matchups, and validate stored source links. Dark responsive UI, mobile navigation, game pages, score/status display, time-zone selection, and protected maintenance are included.

**The default installation uses ESPN's public scoreboard feed** for real NFL schedules and scores, with no API key required. It is an undocumented public endpoint and may change. A licensed SportsDataIO key takes precedence when configured. Development data remains available only with `DATA_PROVIDER=development`.

## Quick start (without Docker)

Prerequisites: Python 3.12+, Node.js 20.19+ (Node 22 recommended), npm. Run commands from the RamanPlay project folder unless another directory is shown.

```sh
python3 scripts/setup_env.py
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open **http://127.0.0.1:3000**. API docs: **http://127.0.0.1:8000/docs**. After dependencies are installed, `sh scripts/dev.sh` starts both processes. Stop with Ctrl+C. Windows users can activate `.venv` and use `python -m uvicorn app.main:app --reload` instead of the POSIX paths above.

The environment helper preserves an existing `.env`, creates random local credentials if missing, and restricts the file permissions. Open `.env` locally and copy `ADMIN_SECRET` into Settings → Maintenance to see counts, refresh the schedule, rebuild sources, or check links. The browser never saves this key. An empty key disables maintenance access; it does not enable anonymous access.

SQLite tables and seed data are created on first startup. The default database is `backend/watch.db`. Relative SQLite paths are resolved against `backend/` consistently for CLI and server runs. The real-data migration adds season phases and nullable networks without replacing records. SQLite creates `backend/watch.db.before-real-data.db` before modifying an older schema. Database files and secrets are ignored by Git. Never publish the development server or a copied `.env`.

## Real schedules and watch-source evidence

The existing `GameDataProvider` abstraction is preserved. Provider selection is automatic: a nonempty `SPORTSDATAIO_API_KEY` selects SportsDataIO; otherwise `DATA_PROVIDER=auto` selects ESPN. A legacy `NFL_DATA_API_KEY` remains accepted for compatibility, but the canonical variable takes precedence. `DATA_PROVIDER=development` retains labeled sample data, and `DATA_PROVIDER=json` remains available for curated imports.

Set these values in the root `.env` locally (never paste your key into source code):

```dotenv
SPORTSDATAIO_API_KEY=your-account-key
NFL_SEASON=
SPORTSDATA_TRIAL=false
DATA_PROVIDER=auto
```

Restart the backend, then use **Settings → Maintenance → Update schedule**, or run:

```sh
backend/.venv/bin/python scripts/update_schedule.py
```

The CLI reports games fetched, created, updated, and errors. Stable provider IDs prevent duplicates; records without IDs use a deterministic season/phase/week/team/kickoff identity. A moved kickoff updates an existing stable-ID record. Unknown kickoff times remain null. Missing broadcaster data remains null and displays as Network unknown. Upcoming games do not display placeholder scores, and previously saved final scores survive incomplete provider updates.

An unset or blank `NFL_SEASON` selects the current season automatically: January and February belong to the previous starting year; March–December use the current year. Set an explicit year to view another season. The adapter requests PRE, REG and POST and stores each game's normalized phase. All timestamps are stored in UTC. All 32 canonical team abbreviations are supported, with provider aliases mapped before storage so favorites retain their existing team IDs.

`SPORTSDATA_TRIAL=true` explicitly marks a scrambled/trial feed as DEVELOPMENT DATA. Only use false for actual production data. The ESPN feed is public and unauthenticated; it is not a contracted API. Your SportsDataIO plan must grant all requested NFL Scores-by-Season feeds. A key alone does not establish production-data entitlement. See [SportsDataIO's API documentation](https://sportsdata.io/developers/api-documentation/nfl) and [data dictionary](https://sportsdata.io/developers/data-dictionary/nfl).

Syncs write to the database; browser reads never call SportsDataIO. Errors preserve the last real schedule for the selected season. If none is cached, the app displays clearly labeled development data. Maintenance shows the active/configured provider, Connected/Error/Not configured, last successful and attempted sync, counts, and a sanitized error message. Partial/malformed imports are not committed. A short request cache deduplicates repeated sync requests and is isolated by season, trial mode, and a hash of the credential.

A local JSON feed still supports every supplied game and explicit game-specific viewing evidence. Set `SCHEDULE_FILE` to its absolute path and use the included schema. The SportsDataIO adapter supplies the official NFL viewing directory as an informational fallback; a TV channel is not assumed to establish streaming entitlement.

For curated sources, use a JSON feed with explicit per-game entries like:

```json
{
  "provider_name": "Verified broadcaster name",
  "source_name": "Exact game listing",
  "url": "https://www.nfl.com/ways-to-watch",
  "source_type": "OFFICIAL_NFL",
  "access_type": "OFFICIAL",
  "region": "Location dependent",
  "notes": "Official directory only; verify the exact game and provider access."
}
```

This is an informational example, not a FREE stream. Supported source types and classification requirements are in `docs/source-policy.md` and `backend/app/schemas/feed.py`. Approved-domain validation runs before storage. FREE must be `FREE_LEGAL` with clear evidence; FREE TRIAL must describe signup, eligibility and renewal. Paid TV authentication is not free. No broadcaster is assumed to carry every game. No search scraping or unauthorized source discovery is used.

## Environment

Copy or generate `.env` from `.env.example`. Important settings:

- `DATABASE_URL`: defaults to local SQLite; use `postgresql+psycopg://...` for PostgreSQL. Relative SQLite filenames resolve inside backend.
- `ADMIN_SECRET`: random bearer key for maintenance; never use a `NEXT_PUBLIC_` variable.
- `SPORTSDATAIO_API_KEY`, `NFL_SEASON`, `SPORTSDATA_TRIAL`: credential-backed schedule configuration.
- `DATA_PROVIDER`: auto (default, ESPN), espn, development, or json. A configured SportsDataIO key takes precedence.
- `SCHEDULE_FILE`: absolute JSON feed path; defaults to the included seed feed.
- `ALLOWED_ORIGINS`: comma-separated exact frontend origins; default localhost/127.0.0.1 on port 3000.
- `TRUSTED_DOMAINS`: optional comma-separated domain whitelist override. Extend carefully for a legitimate provider; network destinations must still be public HTTPS.
- `SCHEDULE_HOURS`: full-import interval, default 6.
- `GAME_DAY_REFRESH_SECONDS`: non-live game-day refresh, minimum 300, default 900.
- `PROVIDER_TIMEOUT_SECONDS`: per-request timeout, default 15.
- `PROVIDER_RETRIES`: transient retry count, default 2; invalid keys and rate limits are not retried immediately.
- `LIVE_REFRESH_SECONDS`: backend active-game refresh interval, minimum 60, default 120.
- `LINK_CHECK_HOURS`: scheduled link-check interval, minimum 1, default 6.
- `REQUEST_INTERVAL_SECONDS`: respectful spacing between requests, default 2.
- `USER_AGENT`: configurable link-check user agent.
- `SCHEDULER_ENABLED`: disable embedded jobs when using a separate scheduler.
- `POSTGRES_PASSWORD`: Docker database secret; generated by the setup helper.

The frontend proxies `/api` through Next.js. To use a separate backend, create `frontend/.env.local` with `BACKEND_URL=https://your-backend.example` **before building**; rewrites are compiled into the build. Browser settings save time zone, favorites, paid/free/audio visibility, and auto-refresh locally. Link-check frequency can be saved in protected Maintenance (1–168 hours), with LINK_CHECK_HOURS as the initial default. Notifications remain disabled.

## API and maintenance

Public reads: `/api/games` (filters), `/api/games/today`, `/api/games/live`, `/api/games/upcoming`, `/api/games/{id}`, `/api/teams`, `/api/teams/{id}`, `/api/sources/{game_id}`, `/api/search`, `/api/favorites`, `/api/health`.

Filters include `q`, `period` (all/today/tomorrow/week/weekend), `tz` (IANA zone), `team`, `conference`, `division`, `network`, `access`, `status`, and `date` (YYYY-MM-DD). Weeks run Monday–Sunday; weekends mean Saturday–Sunday of that week. Search supports team names, multiple teams, Sunday games, free games, and games tonight. Date filters use the selected timezone. Favorites are browser-local; the GET favorites API exposes the reserved database store and is not synced with localStorage.

Protected endpoints: GET `/api/admin/status`; POST `/api/admin/update-schedule`, `/api/admin/rebuild-sources`, `/api/admin/check-links`. Send `Authorization: Bearer <ADMIN_SECRET>`. Settings provides the corresponding controls. Rebuild sources reimports the configured evidence feed; link checks record HEAD/GET results and timestamps. Check links may take minutes because requests are intentionally spaced and repeated URLs are deduplicated.

Local maintenance without HTTP:

```sh
backend/.venv/bin/python scripts/maintain.py update-schedule
backend/.venv/bin/python scripts/maintain.py rebuild-sources
backend/.venv/bin/python scripts/maintain.py check-links
```

## Tests and build

```sh
backend/.venv/bin/pytest -q
cd frontend
npm test
npm run build
npm start
```

Tests cover imports/idempotency, providers, team matching, full-season HTTP normalization, null kickoffs, searches, timezone boundaries, local favorites, API routes, maintenance authentication, domain validation, private DNS, unsafe redirects, link classification, HEAD fallback, robots policy, and persisted/deduplicated checks. No tests access real broadcast streams. Builds use webpack for reliable compilation in this host environment.

## Optional Docker / PostgreSQL

```sh
python3 scripts/setup_env.py
docker compose up --build
```

Open http://localhost:3000. Compose builds frontend/backend targets from the root Dockerfile and starts PostgreSQL with a persistent named volume. Only the frontend is published, bound to loopback; backend/database use the internal network. Both app images run as non-root users. PostgreSQL readiness gates backend startup; backend readiness gates frontend startup. `docker compose down` preserves the database. Do not remove the data volume unless intentionally discarding it. Stop local servers first if port 3000 is already in use.

For a JSON feed in Docker, mount your feed read-only into the backend and set SCHEDULE_FILE to its container path. Backend and frontend have separate image build targets. Docker is optional; its runtime needs Docker Desktop or an equivalent engine installed locally.

## Deployment preparation

Frontend: Vercel or another Next.js Node host. Set root directory `frontend`, install with `npm ci`, build with `npm run build`, and set BACKEND_URL before building. Backend: use the backend Docker target or install Python requirements on Render/Railway/Fly/VPS and run `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`. Supply persistent PostgreSQL, ADMIN_SECRET, exact ALLOWED_ORIGINS, and the desired data provider. Keep one scheduler process; multiple Uvicorn workers would duplicate embedded jobs.

Require HTTPS, restrict maintenance access to yourself, back up the database, and add versioned migrations for future schema changes. Current rate limiting is per process and intended for personal use; add an edge/shared limiter before multi-instance hosting. The application is not an authentication/cloud-favorites service. No deployment has been performed.

## Security and legal boundaries

Only links to legitimate providers are opened, in a new tab with noopener/noreferrer. No video is hosted, embedded, mirrored, proxied, downloaded, or rebroadcast. No paywall, login, DRM, or geo-restriction bypass is attempted. An official domain does not guarantee a free stream; a successful HTTP check does not prove game playback. See `docs/source-policy.md`.

Link checks accept only approved public HTTPS hosts, reject credentials/alternate ports/private IPs, and revalidate redirects. Connections are pinned to validated public IPs while retaining verified TLS and SNI, protecting against DNS rebinding. Robots restrictions and blocks are respected. Responses are capped at 64 KiB and discarded after validation. Structured logs omit credentials and raw exception payloads. API uses explicit CORS, validation, request limits and secure headers. Maintenance is disabled without a key.

## Troubleshooting

- **Games fail to load:** start FastAPI on port 8000; check `/api/health`. If BACKEND_URL changed, restart/rebuild Next.js.
- **Empty Today or Free results:** a full real feed may have no game today; no confirmed free option is a valid result. Demo records are labeled and shift at import time.
- **401 in maintenance:** copy the exact ADMIN_SECRET from the root .env; restart backend after changes.
- **BLOCKED/ERROR links:** a provider may reject automated requests or robots rules may prohibit checks. Do not bypass. Open the official guide manually.
- **Schedule update failure:** confirm credentials/feed entitlement, a valid timezone on every non-null kickoff, known team abbreviations, unique IDs, and approved source URLs. Existing data remains stored.
- **Database schema mismatch after development changes:** back up first and use a schema migration. Startup applies the specific backed-up real-data migration; other future changes require their own migration.
- **Port in use:** stop the earlier server or configure another port and matching BACKEND_URL/origin.

See `docs/architecture.md` for modules, caching, scheduling and extension points.
