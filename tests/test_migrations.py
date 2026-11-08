from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from playtrace.store.db import Database
from playtrace.store.migrations import Migration, MigrationEngine


class ExampleMigrationEngine(MigrationEngine):
    MIGRATIONS = [
        Migration(version=2, description="create alpha", sql="CREATE TABLE alpha (id INTEGER PRIMARY KEY);"),
        Migration(version=3, description="create beta", sql="CREATE TABLE beta (id INTEGER PRIMARY KEY);"),
        Migration(version=4, description="create gamma", sql="CREATE TABLE gamma (id INTEGER PRIMARY KEY);"),
    ]


class BrokenMigrationEngine(MigrationEngine):
    MIGRATIONS = [
        Migration(version=2, description="create alpha", sql="CREATE TABLE alpha (id INTEGER PRIMARY KEY);"),
        Migration(
            version=3,
            description="broken migration",
            sql="CREATE TABLE broken (id INTEGER PRIMARY KEY); INSERT INTO missing_table VALUES (1);",
        ),
    ]


def _seed_version(db: Database, version: int, description: str = "seeded version") -> None:
    with db.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (version, "2026-04-14T00:00:00+00:00", description),
        )
        conn.commit()


@given(st.integers(min_value=1, max_value=4))
def test_migration_engine_applies_all_intermediate_migrations_in_order(
    target_version: int,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / f"sequence-{target_version}.db")
        _seed_version(db, 1)

        ExampleMigrationEngine(db).apply_migrations(target_version)

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT version FROM schema_version ORDER BY version ASC"
            ).fetchall()

        assert [row["version"] for row in rows] == list(range(1, target_version + 1))


def test_migration_engine_rolls_back_failed_migration(tmp_path: Path) -> None:
    db = Database(tmp_path / "rollback.db")
    _seed_version(db, 1)
    engine = BrokenMigrationEngine(db)

    with pytest.raises(sqlite3.DatabaseError):
        engine.apply_migrations(3)

    with db.connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        versions = conn.execute(
            "SELECT version FROM schema_version ORDER BY version ASC"
        ).fetchall()

    assert "broken" not in tables
    assert [row["version"] for row in versions] == [1, 2]


@given(st.integers(min_value=2, max_value=4))
def test_migration_engine_records_applied_versions(
    target_version: int,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / f"recording-{target_version}.db")
        _seed_version(db, 1)

        ExampleMigrationEngine(db).apply_migrations(target_version)

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT version, applied_at, description FROM schema_version ORDER BY version ASC"
            ).fetchall()

        recorded = rows[-1]
        assert recorded["version"] == target_version
        assert recorded["applied_at"].endswith("+00:00")
        assert recorded["description"]


@given(st.integers(min_value=1, max_value=4))
def test_migration_engine_reports_target_version_after_upgrade(
    target_version: int,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / f"invariant-{target_version}.db")
        _seed_version(db, 1)
        engine = ExampleMigrationEngine(db)

        engine.apply_migrations(target_version)

        assert engine.current_version() == target_version


def test_migration_engine_creates_schema_version_table_when_missing(tmp_path: Path) -> None:
    db = Database(tmp_path / "missing-version-table.db")

    engine = MigrationEngine(db)

    assert engine.current_version() == 1

    with db.connect() as conn:
        row = conn.execute(
            "SELECT version, applied_at, description FROM schema_version"
        ).fetchone()

    assert row["version"] == 1
    assert row["applied_at"].endswith("+00:00")
    assert row["description"] == "bootstrap schema"


def test_migration_engine_is_noop_when_current_version_matches_target(tmp_path: Path) -> None:
    db = Database(tmp_path / "noop.db")
    _seed_version(db, 1)
    engine = ExampleMigrationEngine(db)

    engine.apply_migrations(1)

    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]

    assert count == 1


def test_migration_engine_raises_for_newer_database_version(tmp_path: Path) -> None:
    db = Database(tmp_path / "newer.db")
    _seed_version(db, 5)

    with pytest.raises(ValueError, match="newer version"):
        ExampleMigrationEngine(db).apply_migrations(4)


def test_migration_engine_applies_single_migration(tmp_path: Path) -> None:
    db = Database(tmp_path / "single.db")
    _seed_version(db, 1)

    ExampleMigrationEngine(db).apply_migrations(2)

    with db.connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "alpha" in tables


def test_migration_engine_applies_multiple_migrations_in_sequence(tmp_path: Path) -> None:
    db = Database(tmp_path / "multiple.db")
    _seed_version(db, 1)

    ExampleMigrationEngine(db).apply_migrations(4)

    with db.connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"alpha", "beta", "gamma"} <= tables


class QuotedDescriptionMigrationEngine(MigrationEngine):
    MIGRATIONS = [
        Migration(
            version=2,
            description="add 'alpha'; DROP TABLE schema_version; --",
            sql="CREATE TABLE alpha (id INTEGER PRIMARY KEY);",
        ),
    ]


def test_migration_engine_stores_description_verbatim(tmp_path: Path) -> None:
    db = Database(tmp_path / "quoted.db")
    _seed_version(db, 1)

    QuotedDescriptionMigrationEngine(db).apply_migrations(2)

    with db.connect() as conn:
        row = conn.execute(
            "SELECT description FROM schema_version WHERE version = 2"
        ).fetchone()

    assert row["description"] == "add 'alpha'; DROP TABLE schema_version; --"
