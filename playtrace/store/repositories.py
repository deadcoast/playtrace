from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from playtrace.models.enums import (
    Classification,
    ConfidenceLevel,
    RuntimeConfidence,
)
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.utils.clock import Clock

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


class Repository(Generic[T]):
    def __init__(self, db, table_name: str, id_column: str) -> None:
        self.db = db
        self.table_name = table_name
        self.id_column = id_column

    def find_by_id(self, entity_id: str) -> T | None:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE {self.id_column} = ?",
                (entity_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row, conn)

    def find_all(self) -> list[T]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.table_name} ORDER BY {self.id_column} ASC"
            ).fetchall()
            return [self._row_to_entity(row, conn) for row in rows]

    def save(self, entity: T) -> T:
        data = self._entity_to_row(entity)
        columns = list(data.keys())
        values = [data[column] for column in columns]
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column != self.id_column
        )

        with self.db.connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {self.table_name} ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT({self.id_column}) DO UPDATE SET {updates}
                """,
                values,
            )
            self._after_save(entity, conn)
            conn.commit()
            row = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE {self.id_column} = ?",
                (data[self.id_column],),
            ).fetchone()
            assert row is not None
            return self._row_to_entity(row, conn)

    def delete(self, entity_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                f"DELETE FROM {self.table_name} WHERE {self.id_column} = ?",
                (entity_id,),
            )
            conn.commit()

    def _row_to_entity(self, row: sqlite3.Row, conn: sqlite3.Connection) -> T:
        raise NotImplementedError

    def _entity_to_row(self, entity: T) -> dict[str, object]:
        raise NotImplementedError

    def _after_save(self, entity: T, conn: sqlite3.Connection) -> None:
        return None

    def _optional_enum(
        self,
        enum_type: type[EnumT],
        value: str | None,
    ) -> EnumT | None:
        if not value:
            return None
        try:
            return enum_type(value)
        except ValueError:
            return None

    def _json_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []


class ExecutableRepository(Repository[ExecutableIdentity]):
    def __init__(self, db) -> None:
        super().__init__(db, "executables", "exe_id")

    def find_by_normalized_key(self, key: str) -> ExecutableIdentity | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM executables WHERE normalized_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row, conn)

    def _row_to_entity(
        self,
        row: sqlite3.Row,
        conn: sqlite3.Connection,
    ) -> ExecutableIdentity:
        return ExecutableIdentity(
            exe_id=row["exe_id"],
            normalized_key=row["normalized_key"],
            path=row["path"],
            filename=row["filename"],
            original_filename=row["original_filename"],
            product_name=row["product_name"],
            file_description=row["file_description"],
            signer=row["signer"],
            company_name=row["company_name"],
            sha1=row["sha1"],
            canonical_path=row["path"],
            classification=self._optional_enum(Classification, row["classification"])
            or Classification.UNKNOWN,
            classification_confidence=self._optional_enum(
                ConfidenceLevel,
                row["classification_confidence"],
            )
            or ConfidenceLevel.UNKNOWN,
            ignored=bool(row["ignored"]),
            first_seen=Clock.parse_iso8601(row["first_seen"]),
            last_seen=Clock.parse_iso8601(row["last_seen"]),
        )

    def _entity_to_row(self, entity: ExecutableIdentity) -> dict[str, object]:
        return {
            "exe_id": entity.exe_id,
            "normalized_key": entity.normalized_key,
            "path": entity.canonical_path or entity.path,
            "filename": entity.filename,
            "original_filename": entity.original_filename,
            "product_name": entity.product_name,
            "file_description": entity.file_description,
            "signer": entity.signer,
            "company_name": entity.company_name,
            "sha1": entity.sha1,
            "classification": entity.classification.value,
            "classification_confidence": entity.classification_confidence.value,
            "ignored": 1 if entity.ignored else 0,
            "first_seen": Clock.format_iso8601(entity.first_seen),
            "last_seen": Clock.format_iso8601(entity.last_seen),
        }


class SessionRepository(Repository[SessionRecord]):
    def __init__(self, db) -> None:
        super().__init__(db, "sessions", "session_id")

    def find_by_exe_id(self, exe_id: str) -> list[SessionRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE exe_id = ? ORDER BY session_id ASC",
                (exe_id,),
            ).fetchall()
            return [self._row_to_entity(row, conn) for row in rows]

    def _row_to_entity(self, row: sqlite3.Row, conn: sqlite3.Connection) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            title_id=row["title_id"],
            exe_id=row["exe_id"],
            user_sid=row["user_sid"],
            started_at=Clock.parse_iso8601(row["started_at"]),
            ended_at=Clock.parse_iso8601(row["ended_at"]),
            duration_seconds=row["duration_seconds"],
            foreground_seconds=int(row["foreground_seconds"] or 0),
            bytes_in=int(row["bytes_in"] or 0),
            bytes_out=int(row["bytes_out"] or 0),
            confidence=self._optional_enum(RuntimeConfidence, row["confidence"])
            or RuntimeConfidence.UNKNOWN,
            evidence_sources=self._json_list(row["evidence_sources"]),
            evidence_ids=self._json_list(row["evidence_ids"]),
            parent_chain=self._json_list(row["parent_chain"]),
            notes=self._json_list(row["notes"]),
        )

    def _entity_to_row(self, entity: SessionRecord) -> dict[str, object]:
        return {
            "session_id": entity.session_id,
            "title_id": entity.title_id,
            "exe_id": entity.exe_id,
            "user_sid": entity.user_sid,
            "started_at": Clock.format_iso8601(entity.started_at),
            "ended_at": Clock.format_iso8601(entity.ended_at),
            "duration_seconds": entity.duration_seconds,
            "foreground_seconds": entity.foreground_seconds,
            "bytes_in": entity.bytes_in,
            "bytes_out": entity.bytes_out,
            "confidence": entity.confidence.value,
            "evidence_sources": json.dumps(entity.evidence_sources),
            "evidence_ids": json.dumps(entity.evidence_ids),
            "parent_chain": json.dumps(entity.parent_chain),
            "notes": json.dumps(entity.notes),
        }


class TitleRepository(Repository[TitleAggregate]):
    def __init__(self, db) -> None:
        super().__init__(db, "titles", "title_id")

    def find_by_classification(self, classification: Classification) -> list[TitleAggregate]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM titles WHERE classification = ? ORDER BY title ASC",
                (classification.value,),
            ).fetchall()
            return [self._row_to_entity(row, conn) for row in rows]

    def _row_to_entity(self, row: sqlite3.Row, conn: sqlite3.Connection) -> TitleAggregate:
        executable_ids = [
            relation["exe_id"]
            for relation in conn.execute(
                """
                SELECT exe_id
                FROM title_executables
                WHERE title_id = ?
                ORDER BY rowid ASC
                """,
                (row["title_id"],),
            ).fetchall()
        ]
        return TitleAggregate(
            title_id=row["title_id"],
            title=row["title"],
            classification=self._optional_enum(Classification, row["classification"])
            or Classification.UNKNOWN,
            classification_confidence=self._optional_enum(
                ConfidenceLevel,
                row["classification_confidence"],
            )
            or ConfidenceLevel.UNKNOWN,
            title_confidence=self._optional_enum(
                ConfidenceLevel,
                row["title_confidence"],
            )
            or ConfidenceLevel.UNKNOWN,
            launcher=row["launcher"],
            runtime=RuntimeStats(
                confirmed_seconds=int(row["confirmed_seconds"] or 0),
                estimated_seconds=int(row["estimated_seconds"] or 0),
                foreground_seconds=int(row["foreground_seconds"] or 0),
                confidence=self._optional_enum(ConfidenceLevel, row["runtime_confidence"])
                or ConfidenceLevel.UNKNOWN,
            ),
            launches=LaunchStats(
                confirmed=int(row["launches_confirmed"] or 0),
                inferred=int(row["launches_inferred"] or 0),
                gui=int(row["launches_gui"] or 0),
                confidence=self._optional_enum(ConfidenceLevel, row["launches_confidence"])
                or ConfidenceLevel.UNKNOWN,
            ),
            first_seen=Clock.parse_iso8601(row["first_seen"]),
            last_seen=Clock.parse_iso8601(row["last_seen"]),
            executable_ids=executable_ids,
            evidence_sources=self._json_list(row["evidence_sources"]),
            tags=self._json_list(row["tags"]),
            notes=self._json_list(row["notes"]),
        )

    def _entity_to_row(self, entity: TitleAggregate) -> dict[str, object]:
        return {
            "title_id": entity.title_id,
            "title": entity.title,
            "classification": entity.classification.value,
            "classification_confidence": entity.classification_confidence.value,
            "title_confidence": entity.title_confidence.value,
            "launcher": entity.launcher,
            "confirmed_seconds": entity.runtime.confirmed_seconds,
            "estimated_seconds": entity.runtime.estimated_seconds,
            "foreground_seconds": entity.runtime.foreground_seconds,
            "runtime_confidence": entity.runtime.confidence.value,
            "launches_confirmed": entity.launches.confirmed,
            "launches_inferred": entity.launches.inferred,
            "launches_gui": entity.launches.gui,
            "launches_confidence": entity.launches.confidence.value,
            "first_seen": Clock.format_iso8601(entity.first_seen),
            "last_seen": Clock.format_iso8601(entity.last_seen),
            "evidence_sources": json.dumps(entity.evidence_sources),
            "tags": json.dumps(entity.tags),
            "notes": json.dumps(entity.notes),
        }

    def _after_save(self, entity: TitleAggregate, conn: sqlite3.Connection) -> None:
        conn.execute(
            "DELETE FROM title_executables WHERE title_id = ?",
            (entity.title_id,),
        )
        conn.executemany(
            """
            INSERT INTO title_executables (title_id, exe_id)
            VALUES (?, ?)
            """,
            [(entity.title_id, exe_id) for exe_id in entity.executable_ids],
        )


class MappingRepository(Repository[UserMapping]):
    def __init__(self, db) -> None:
        super().__init__(db, "mappings", "mapping_id")
        self._normalizer = IdentityNormalizer()

    def find_by_target(self, target: str) -> UserMapping | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM mappings WHERE target = ?",
                (target,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row, conn)

    def _row_to_entity(self, row: sqlite3.Row, conn: sqlite3.Connection) -> UserMapping:
        return UserMapping(
            mapping_id=row["mapping_id"],
            target=row["target"],
            title=row["title"],
            classification=self._optional_enum(Classification, row["classification"]),
            launcher=row["launcher"],
            ignore=bool(row["ignore"]),
            created_at=Clock.parse_iso8601(row["created_at"]) or datetime.min,
            normalized_key=self._normalizer.normalize_executable_target(row["target"]),
            confidence=self._optional_enum(ConfidenceLevel, row["confidence"])
            or ConfidenceLevel.HIGH,
        )

    def _entity_to_row(self, entity: UserMapping) -> dict[str, object]:
        return {
            "mapping_id": entity.mapping_id,
            "target": entity.target,
            "title": entity.title,
            "classification": entity.classification.value if entity.classification else None,
            "launcher": entity.launcher,
            "ignore": 1 if entity.ignore else 0,
            "created_at": Clock.format_iso8601(entity.created_at),
            "confidence": entity.confidence.value,
        }
