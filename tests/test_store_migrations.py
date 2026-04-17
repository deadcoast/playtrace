from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from playtrace.store.db import Database
from playtrace.store.migrations import Migration, MigrationEngine


def test_current_version_bootstraps_schema_version_table(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    engine = MigrationEngine(db)

    assert engine.current_version() == 1

    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "schema_version" in names
    assert "executables" in names


def test_apply_migrations_runs_intermediate_versions(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    engine = MigrationEngine(
        db,
        migrations=[
            Migration(2, "add demo table", "CREATE TABLE demo_one (value TEXT);"),
            Migration(3, "add demo index", "CREATE TABLE demo_two (value TEXT);"),
        ],
    )

    engine.apply_migrations(3)

    assert engine.current_version() == 3
    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"demo_one", "demo_two"} <= names


def test_apply_migrations_is_noop_when_current_version_matches_target(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    engine = MigrationEngine(db)

    engine.apply_migrations(1)

    with db.connect() as conn:
        rows = conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()

    assert [row["version"] for row in rows] == [1]


def test_apply_migrations_rejects_newer_database_versions(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    engine = MigrationEngine(db)
    engine.current_version()

    with db.connect() as conn:
        conn.execute("DELETE FROM schema_version")
        conn.execute(
            """
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (99, '2026-04-17T19:00:00+00:00', 'future version')
            """
        )
        conn.commit()

    with pytest.raises(ValueError, match="newer version"):
        engine.apply_migrations(1)


def test_failed_migration_rolls_back_database_changes(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    engine = MigrationEngine(
        db,
        migrations=[
            Migration(
                2,
                "broken migration",
                "CREATE TABLE demo_failure (value TEXT); INSERT INTO missing_table VALUES (1);",
            )
        ],
    )

    with pytest.raises(sqlite3.Error):
        engine.apply_migrations(2)

    assert engine.current_version() == 1
    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "demo_failure" not in names
