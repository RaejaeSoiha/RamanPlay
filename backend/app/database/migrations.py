"""Small versioned migration preserving existing games and dependent records."""

from sqlalchemy import inspect


def migrate(engine):
    inspector = inspect(engine)
    if "games" not in inspector.get_table_names():
        return
    columns = {c["name"]: c for c in inspector.get_columns("games")}
    personal_columns = (
        {c["name"] for c in inspector.get_columns("personal_links")}
        if "personal_links" in inspector.get_table_names()
        else set()
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
