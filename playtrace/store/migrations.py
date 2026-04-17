from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from playtrace.store.schema import SCHEMA_SQL
from playtrace.utils.clock import Clock


@dataclass(slots=True)
class Migration:
    version: int
    description: str
    sql: str


class MigrationEngine:
    def __init__(self, db, migrations: Iterable[Migration] | None = None) -> None:
        self.db = db
        self._migrations = sorted(list(migrations or []), key=lambda migration: migration.version)

    @property
    def migrations(self) -> list[Migration]:
        return list(self._migrations)

    def current_version(self) -> int:
        self._ensure_version_table()
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT MAX(version) AS version FROM schema_version"
            ).fetchone()
        return int(row["version"] or 1)

    def apply_migrations(self, target_version: int | None = None) -> None:
        current = self.current_version()
        target = target_version if target_version is not None else self._latest_version()

        if current > target:
            raise ValueError("Database schema is from a newer version")
        if current == target:
            return

        available = {migration.version: migration for migration in self._migrations}
        for version in range(current + 1, target + 1):
            migration = available.get(version)
            if migration is None:
                raise ValueError(f"Missing migration for version {version}")
            self._apply_migration(migration)

    def _ensure_version_table(self) -> None:
        with self.db.connect() as conn:
            exists = conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'schema_version'
                """
            ).fetchone()
            if exists:
                return

            conn.executescript(SCHEMA_SQL)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    description TEXT NOT NULL
                )
                """
            )
            self._record_migration(conn, 1, "bootstrap schema")
            conn.commit()

    def _apply_migration(self, migration: Migration) -> None:
        with self.db.connect() as conn:
            conn.execute("BEGIN")
            try:
                for statement in self._split_sql(migration.sql):
                    conn.execute(statement)
                self._record_migration(conn, migration.version, migration.description)
            except sqlite3.Error:
                conn.rollback()
                raise
            conn.commit()

    def _record_migration(
        self,
        conn: sqlite3.Connection,
        version: int,
        description: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (?, ?, ?)
            """,
            (
                version,
                Clock.format_iso8601(Clock.utc_now()),
                description,
            ),
        )

    def _latest_version(self) -> int:
        return max([1, *(migration.version for migration in self._migrations)])

    def _split_sql(self, sql: str) -> list[str]:
        return [statement.strip() for statement in sql.split(";") if statement.strip()]
