# RamanPlay

**All Your Games. One Place.**

RamanPlay is a personal sports dashboard for **NFL**, **NBA**, and **UFC**. It combines schedules, live status and scores, team or fighter pages, standings or rankings, favorites, search, official watch options, and personal My Links in one responsive interface.

RamanPlay uses FastAPI, SQLite or PostgreSQL, and Next.js. NFL, NBA, and UFC data are normalized from the configured provider integrations. My Links are user-entered links only: RamanPlay does not discover, proxy, rehost, embed external webpages, or bypass provider controls.

## Local setup

Requirements: Python 3.12+, Node.js 20.19+ (Node 22 recommended), and npm.

Install backend and frontend dependencies once from the project root:

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Copy the environment template if you need to change defaults:

```sh
cp .env.example .env
```

Start both services with one command:

```sh
npm start
```

- Frontend: <http://127.0.0.1:3000>
- Backend API: <http://127.0.0.1:8000>
- API health: <http://127.0.0.1:8000/api/health>

`Ctrl+C` stops both processes. You can also run `npm run backend` and `npm run frontend` separately. The backend command always uses `backend/.venv/bin/python`; it never relies on a global Uvicorn installation.

## Configuration

`.env` is local and ignored by Git. Important settings:

- `DATABASE_URL` — defaults to `backend/watch.db`; use a persistent PostgreSQL URL in production.
- `ADMIN_SECRET` — enables maintenance endpoints. Leave blank to disable them.
- `SESSION_SECRET` — set a persistent random value in production so household sessions survive a restart.
- `SESSION_SECURE_COOKIE=true` — required for HTTPS production deployments.
- `ALLOWED_ORIGINS` — comma-separated exact frontend origins.
- `DATA_PROVIDER` — `auto` (default ESPN), `espn`, `development`, or `json` for NFL data.
- `SPORTSDATAIO_API_KEY` — optional licensed NFL provider key. When present, it takes precedence.
- `BACKEND_URL` — set in `frontend/.env.local` before building when the Next.js frontend proxies to a separate backend.

NBA and UFC use their existing ESPN integrations and do not require an additional key. Never commit `.env`, database files, or provider credentials.

## Sports news

RamanPlay uses ESPN's public NFL, NBA, and UFC headline feeds for short, provider-supplied story metadata and original article links. `GET /api/news?sport=ALL|NFL|NBA|UFC&limit=6` returns up to 12 stories. Each league feed is cached in memory for five minutes; stale cached headlines are used when ESPN is temporarily unavailable. RamanPlay does not fetch full article bodies or embed publisher pages.

## Post-game recaps

`GET /api/recaps?sport=ALL|NFL|NBA|UFC&limit=5` produces factual final results from RamanPlay's stored normalized games, events, teams, and UFC bouts. Detail data is available at `GET /api/recaps/{sport}/{id}`. Recaps do not make upstream requests and omit player statistics, quarter scoring, or fight details when the configured provider has not supplied them.

## My Links and playback

Official provider links and manually entered My Links remain visually separate. A manually entered public HTTPS link can be saved as **UNVERIFIED** after URL and SSRF validation; it requires confirmation before external navigation. Trusted domains are **VERIFIED**. Suspicious redirects are **WARNING** and unsafe URLs or destinations are **BLOCKED**.

Only checked, eligible direct-media URLs can play in RamanPlay’s native inline video player. External webpages never render in an iframe, object, or embed. RamanPlay does not remove third-party ads, scrape media URLs, bypass authentication, DRM, subscriptions, geo restrictions, or access controls.

## Architecture

- `frontend/app/` contains stable Next.js routes.
- `frontend/features/nfl`, `frontend/features/nba`, and `frontend/features/ufc` contain sport-specific UI.
- `frontend/components/watch` and `frontend/components/player` contain shared My Links and native playback UI.
- `backend/app/sports/` contains NFL, NBA, and UFC ingestion/parsing.
- `backend/app/watch/` contains shared URL validation, link checking, reliability, and Best Link logic.
- `backend/app/api/routes.py` remains the stable API facade.

See [docs/architecture.md](docs/architecture.md) for the complete source map and extension guidance.

## Validation

```sh
# Frontend type check and targeted tests
cd frontend
npx tsc --noEmit
npx vitest run

# Backend tests
cd ../backend
.venv/bin/python -m pytest ../tests/backend -q
```

For a production frontend build:

```sh
npm --prefix frontend run build
```

The existing Docker configuration builds the frontend and backend targets with PostgreSQL. Before deployment, set a persistent database, a strong `ADMIN_SECRET`, `SESSION_SECRET`, exact `ALLOWED_ORIGINS`, `SESSION_SECURE_COOKIE=true`, and run a single scheduler-enabled backend worker. No deployment is performed by this repository.
