from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from playtrace.store.db import Database
from playtrace.utils.clock import Clock

SCHEMA_VERSION_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
)
"""


@dataclass(slots=True, frozen=True)
class Migration:
    version: int
    description: str
    sql: str


class MigrationEngine:
    BASE_VERSION = 1
    BASE_DESCRIPTION = "bootstrap schema"
    MIGRATIONS: list[Migration] = []

    def __init__(self, db: Database) -> None:
        self.db = db

    def current_version(self) -> int:
        self._ensure_version_table()

        with self.db.connect() as conn:
            row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()

        return int(row["version"] or self.BASE_VERSION)

    def apply_migrations(self, target_version: int) -> None:
        self._ensure_version_table()
        current_version = self.current_version()

        if current_version > target_version:
            raise ValueError(
                f"Database is at newer version {current_version} than target version {target_version}"
            )
        if current_version == target_version:
            return

        migration_map = {migration.version: migration for migration in self.migrations}
        for version in range(current_version + 1, target_version + 1):
            migration = migration_map.get(version)
            if migration is None:
                raise ValueError(f"Missing migration for target version {version}")
            self._apply_migration(migration)

    def _ensure_version_table(self) -> None:
        with self.db.connect() as conn:
            conn.execute(SCHEMA_VERSION_SQL)
            row = conn.execute("SELECT COUNT(*) AS count FROM schema_version").fetchone()
            if int(row["count"] or 0) == 0:
                conn.execute(
                    """
                    INSERT INTO schema_version (version, applied_at, description)
                    VALUES (?, ?, ?)
                    """,
                    (
                        self.BASE_VERSION,
                        self._timestamp(),
                        self.BASE_DESCRIPTION,
                    ),
                )
            conn.commit()

    def _apply_migration(self, migration: Migration) -> None:
        # executescript() cannot bind parameters, so the DDL runs as a script inside an
        # explicit transaction that is left open; the version row is then inserted with
        # bound parameters and both are committed (or rolled back) together.
        script = f"BEGIN;\n{migration.sql.rstrip().rstrip(';')};\n"

        with self.db.connect() as conn:
            try:
                conn.executescript(script)
                conn.execute(
                    """
                    INSERT INTO schema_version (version, applied_at, description)
                    VALUES (?, ?, ?)
                    """,
                    (migration.version, self._timestamp(), migration.description),
                )
                conn.commit()
            except sqlite3.DatabaseError:
                conn.rollback()
                raise

    @property
    def migrations(self) -> list[Migration]:
        return sorted(self.MIGRATIONS, key=lambda migration: migration.version)

    def _timestamp(self) -> str:
        now = Clock.utc_now()
        return Clock.format_iso8601(now) or now.isoformat()
