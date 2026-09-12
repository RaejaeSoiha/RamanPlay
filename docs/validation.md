# Validation — September 11, 2026

- Backend: 50 pytest tests passed. Two dependency deprecation warnings from Starlette's test-client integration; no failed assertions.
- Frontend: four Vitest tests passed; Next.js production build and TypeScript checks passed.
- Dependency consistency: pip check passed. npm audit after upgrading Vitest reported zero vulnerabilities.
- Browser: dashboard and game details rendered; following Denver persisted across reloads; matchup search returned the correct game; mobile layout at 390px had no horizontal overflow. Default viewport restored after testing.
- Maintenance integration: unauthorized status denied; generated local key accepted; schedule update and status returned success without exposing credentials.
- Real link-check run: 17 records, two unique official URLs. Both returned BLOCKED because their robots policy disallowed checking or could not be verified. No bypass attempted; BLOCKED does not prove a website is offline or a stream is available. An initial host certificate error was corrected by using the installed certifi trust bundle with normal TLS verification.
- Docker Compose configuration validated. Container build/run could not be exercised: the Docker engine is stopped, and desktop permissions prevented starting it. Start Docker Desktop and run `docker compose up --build` to complete container validation.
- SportsDataIO adapter tested using mocked authenticated HTTP responses, including PRE/REG/POST, aliases, halftime and unknown kickoffs. Licensed live API access is not verified because no account key was provided.
- No public deployment was attempted. Default visible data is DEVELOPMENT DATA.

All project source, tests, configuration, and documentation were created in this new workspace; no pre-existing application files were overwritten. The generated local database and .env are excluded from version control.

## Real-data follow-up

135 backend tests, 13 frontend tests, and the production build passed. The original tests continue passing. Two real local CLI runs used the development fallback (no API key), each fetching 16 games, creating zero, updating 16, with zero errors. Existing SQLite data was migrated with a backup. SportsDataIO success/failure cases and real-mode API metadata were tested with mocked HTTP. See real-data.md for changed files, operator configuration, and limitations.
