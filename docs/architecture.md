# Architecture and extension points

Next.js renders a responsive browser client and proxies `/api/*` to FastAPI. No API key is shipped to the browser. SQLAlchemy stores teams, games, per-game source evidence, favorites (reserved for future opt-in synchronization), link-check history and maintenance state. SQLite is local; Docker uses PostgreSQL.

`GameDataProvider` separates schedule ingestion from transport. `DevelopmentProvider` builds relative-date samples so Today can be demonstrated, while `JsonScheduleProvider` imports every supplied game. `SportsDataProvider` imports PRE/REG/POST with a header-only API key and a short-lived request cache. Unknown kickoff times remain null and display as unannounced. Games are scoped by provider to separate samples and real data. The development feed includes one simulated live score and one subscription example, both prominently labeled. Production data must never be substituted silently on failure. `WatchSourceProvider` validates and classifies each game-specific source; the official NFL directory is a fallback informational link, never a free broadcast. No network-to-provider assumption creates a streaming entitlement.

The database is the persistent schedule, team, and source cache. Browser refreshes do not fetch any outside provider. Identical link URLs are checked once per run and persisted separately for each game. APScheduler has a configurable full import (default six hours), configurable status/source refresh, and a periodic link check. Run only one backend worker while the embedded scheduler is enabled; use a dedicated scheduler process for horizontal deployment.

Link-checking uses TLS-verified sockets pinned to a resolved, public address. The Host header and TLS SNI retain the approved hostname. Every redirect undergoes validation again. Robots rules, a configurable interval, bounded retries and HEAD-first requests limit impact. Reads are bounded to 64 KiB. No response bodies are stored or served to users. An ONLINE result indicates HTTP reachability, never game availability, region eligibility, or successful playback.

Maintenance uses a constant-time bearer-key comparison, disabled when ADMIN_SECRET is empty. The key lives in page memory only. Rate limits are process-local; use one worker locally and an edge/shared limiter when hosting. The current HTTP favorites endpoint represents the reserved database store; browser favorites intentionally remain in localStorage and never sync without opt-in. Notification transport is deliberately disabled.

Database tables are created on startup for a fresh installation. For future schema revisions use versioned migrations and backups; the real-data migration adds season_type and nullable broadcaster fields to existing games, preserving IDs and source relationships; SQLite takes a backup first. `create_all` alone does not migrate other future changes. PostgreSQL URLs require the `postgresql+psycopg` driver prefix. No deployment is performed by this project setup.

See `real-data.md` for automatic provider selection, fallback semantics, sync status, and verification.

## Source organization

RamanPlay is organized around sport domains while keeping routing, data models, provider transport, and watch safety shared.

### Frontend

- `frontend/app/` contains stable Next.js routes only. Public URLs do not depend on component locations.
- `frontend/components/layout/` contains the shared application shell and dashboard orchestration.
- `frontend/components/shared/` contains UI used by more than one sport: team profiles, standings, game utilities, badges, and crests.
- `frontend/components/player/` contains the native inline video player.
- `frontend/components/watch/` contains My Links UI and its shared opening flow.
- `frontend/components/home/`, `components/sports/`, and `components/settings/` contain global feature areas.
- `frontend/features/nfl/`, `features/nba/`, and `features/ufc/` hold sport-specific components and helpers. UFC filters live with the UFC feature because they use event/fight-card concepts.
- `frontend/lib/sports/registry.ts` is the source of sport metadata: route segments, supported views, logos, and capabilities. `frontend/lib/sportRoutes.ts` is a compatibility export.
- `frontend/lib/myLinks.ts` and `frontend/lib/playback.ts` remain shared because the same reliability, Best Link, and playback rules apply to every sport.

The former top-level files in `frontend/components/` are intentionally tiny compatibility exports. They preserve existing internal imports while the implementation lives in its domain folder. New code should import the organized locations directly.

### Backend

- `backend/app/sports/nfl/players.py` contains NFL roster parsing.
- `backend/app/sports/nba/games.py` and `backend/app/sports/nba/players.py` contain NBA schedule and player ingestion.
- `backend/app/sports/ufc/events.py` contains UFC event, bout, and fighter ingestion.
- `backend/app/watch/security.py`, `watch/checker.py`, and `watch/links.py` contain shared URL validation, SSRF protections, redirect checking, reliability, and Best Link logic.
- `backend/app/services/espn.py`, `services/sportsdata.py`, and `services/providers.py` remain shared provider infrastructure. Sport modules own provider-specific parsing; HTTP/provider selection remains centralized.
- `backend/app/models/` and `database/` remain unchanged to preserve table names, migrations, and existing user data.
- `backend/app/api/routes.py` remains the stable API facade. It is intentionally not split during this refactor because its public route dependencies are broad; new endpoint groups should be extracted only with focused API tests.

The old `app.services.nba`, `nba_players`, `nfl_players`, `ufc`, `checker`, `personal_links`, and `security` modules are compatibility exports. New backend code should import from `app.sports.*` or `app.watch.*`.

### Tests

Tests keep their established filenames so existing targeted commands and direct links remain valid. Their names identify the domain: `test_nba.py`, `test_ufc.py`, `test_nfl_players.py`, `test_my_links.py`, and their frontend equivalents. New tests should follow this domain naming and be placed in a dedicated subdirectory only when a domain needs multiple files.

### Adding a future sport

1. Add one entry to `frontend/lib/sports/registry.ts` with its route segment and capabilities.
2. Add sport routes under `frontend/app/sports/` only when its view requirements differ from the existing dynamic sport route.
3. Add frontend code under `frontend/features/<sport>/`.
4. Add backend ingestion/parsing under `backend/app/sports/<sport>/`.
5. Reuse `app/watch/`, shared player/video components, models, and provider infrastructure unless the sport needs a real new concept.
6. Add domain-named tests and keep existing URLs, stored My Links, and data models compatible.
