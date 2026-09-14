"""Small versioned migration preserving existing games and dependent records."""

from sqlalchemy import inspect


def migrate(engine):
    inspector = inspect(engine)
    if "games" not in inspector.get_table_names():
        return
    columns = {c["name"]: c for c in inspector.get_columns("games")}
    team_columns = (
        {c["name"] for c in inspector.get_columns("teams")}
        if "teams" in inspector.get_table_names()
        else set()
    )
    personal_columns = (
        {c["name"] for c in inspector.get_columns("personal_links")}
        if "personal_links" in inspector.get_table_names()
        else set()
    )
    personal_game = personal_columns and next(
        (column for column in inspector.get_columns("personal_links") if column["name"] == "game_id"),
        None,
    )
    needs_change = (
        "season_type" not in columns or not columns["broadcast_network"]["nullable"]
    )
    if (
        needs_change
        and engine.dialect.name == "sqlite"
        and engine.url.database not in (None, ":memory:")
    ):
        import sqlite3
        from pathlib import Path

        backup = Path(engine.url.database + ".before-real-data.db")
        if not backup.exists():
            with (
                sqlite3.connect(engine.url.database) as source,
                sqlite3.connect(backup) as destination,
            ):
                source.backup(destination)
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        if "season_type" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE games ADD COLUMN season_type VARCHAR NOT NULL DEFAULT 'REGULAR'"
            )
        game_additions = {
            "sport": "VARCHAR(32) NOT NULL DEFAULT 'FOOTBALL'",
            "league": "VARCHAR(16) NOT NULL DEFAULT 'NFL'",
            "away_record": "VARCHAR(32)",
            "home_record": "VARCHAR(32)",
        }
        for name, definition in game_additions.items():
            if name not in columns:
                conn.exec_driver_sql(f"ALTER TABLE games ADD COLUMN {name} {definition}")
        team_additions = {
            "provider_abbreviation": "VARCHAR(8)",
            "provider_id": "VARCHAR(32)",
            "sport": "VARCHAR(32) NOT NULL DEFAULT 'FOOTBALL'",
            "league": "VARCHAR(16) NOT NULL DEFAULT 'NFL'",
        }
        for name, definition in team_additions.items():
            if name not in team_columns:
                conn.exec_driver_sql(f"ALTER TABLE teams ADD COLUMN {name} {definition}")
        conn.exec_driver_sql(
            "UPDATE teams SET provider_abbreviation=abbreviation WHERE provider_abbreviation IS NULL"
        )
        if columns["broadcast_network"]["nullable"] is False:
            if engine.dialect.name == "sqlite":
                conn.exec_driver_sql(
                    "ALTER TABLE games RENAME COLUMN broadcast_network TO old_network"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE games ADD COLUMN broadcast_network VARCHAR"
                )
                conn.exec_driver_sql(
                    "UPDATE games SET broadcast_network = NULLIF(NULLIF(old_network, 'TBA'), '')"
                )
                conn.exec_driver_sql("ALTER TABLE games DROP COLUMN old_network")
            else:
                conn.exec_driver_sql(
                    "ALTER TABLE games ALTER COLUMN broadcast_network DROP NOT NULL"
                )
                conn.exec_driver_sql(
                    "UPDATE games SET broadcast_network=NULL WHERE broadcast_network IN ('TBA','')"
                )
        personal_additions = {
            "last_successful_check": "DATETIME",
            "last_failure": "DATETIME",
            "successful_check_count": "INTEGER NOT NULL DEFAULT 0",
            "failure_count": "INTEGER NOT NULL DEFAULT 0",
            "average_response_time": "FLOAT NOT NULL DEFAULT 0",
            "redirect_count": "INTEGER NOT NULL DEFAULT 0",
            "final_destination_domain": "VARCHAR(255)",
            "last_opened_at": "DATETIME",
            "playback_preference": "VARCHAR(32) NOT NULL DEFAULT 'AUTO'",
            "playback_type": "VARCHAR(32) NOT NULL DEFAULT 'EXTERNAL_PAGE'",
        }
        for name, definition in personal_additions.items():
            if name not in personal_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE personal_links ADD COLUMN {name} {definition}"
                )
        if "shared_with_household" not in personal_columns:
            conn.exec_driver_sql(
                "ALTER TABLE personal_links ADD COLUMN shared_with_household BOOLEAN NOT NULL DEFAULT 0"
            )
        if "owner_id" not in personal_columns:
            conn.exec_driver_sql("ALTER TABLE personal_links ADD COLUMN owner_id INTEGER")
        if "event_id" not in personal_columns:
            conn.exec_driver_sql("ALTER TABLE personal_links ADD COLUMN event_id INTEGER")
        if personal_game and not personal_game["nullable"]:
            if engine.dialect.name == "sqlite":
                conn.exec_driver_sql(
                    "CREATE TABLE personal_links_new ("
                    "id INTEGER NOT NULL PRIMARY KEY, game_id INTEGER, event_id INTEGER, owner_id INTEGER, "
                    "url VARCHAR(2048) NOT NULL, source_name VARCHAR(100) NOT NULL, notes TEXT NOT NULL DEFAULT '', "
                    "priority INTEGER NOT NULL DEFAULT 3, enabled BOOLEAN NOT NULL DEFAULT 1, status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN', playback_preference VARCHAR(32) NOT NULL DEFAULT 'AUTO', playback_type VARCHAR(32) NOT NULL DEFAULT 'EXTERNAL_PAGE', "
                    "final_url VARCHAR(2048), last_checked DATETIME, last_successful_check DATETIME, last_failure DATETIME, "
                    "successful_check_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0, "
                    "average_response_time FLOAT NOT NULL DEFAULT 0, redirect_count INTEGER NOT NULL DEFAULT 0, "
                    "final_destination_domain VARCHAR(255), last_opened_at DATETIME, shared_with_household BOOLEAN NOT NULL DEFAULT 0, "
                    "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
                )
                conn.exec_driver_sql(
                    "INSERT INTO personal_links_new (id, game_id, event_id, owner_id, url, source_name, notes, priority, enabled, status, playback_preference, playback_type, final_url, last_checked, last_successful_check, last_failure, successful_check_count, failure_count, average_response_time, redirect_count, final_destination_domain, last_opened_at, shared_with_household, created_at, updated_at) "
                    "SELECT id, game_id, event_id, owner_id, url, source_name, notes, priority, enabled, status, playback_preference, playback_type, final_url, last_checked, last_successful_check, last_failure, successful_check_count, failure_count, average_response_time, redirect_count, final_destination_domain, last_opened_at, shared_with_household, created_at, updated_at FROM personal_links"
                )
                conn.exec_driver_sql("DROP TABLE personal_links")
                conn.exec_driver_sql("ALTER TABLE personal_links_new RENAME TO personal_links")
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_personal_links_game_id ON personal_links (game_id)")
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_personal_links_event_id ON personal_links (event_id)")
            else:
                conn.exec_driver_sql("ALTER TABLE personal_links ALTER COLUMN game_id DROP NOT NULL")
