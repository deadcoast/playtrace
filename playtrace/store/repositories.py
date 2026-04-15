from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.db import Database
from playtrace.utils.clock import Clock

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


class Repository(Generic[T], ABC):
    def __init__(
        self,
        db: Database,
        *,
        id_column: str,
        write_columns: tuple[str, ...],
        select_by_id_sql: str,
        select_all_sql: str,
        upsert_sql: str,
        delete_sql: str,
    ) -> None:
        self.db = db
        self.id_column = id_column
        self._write_columns = write_columns
        self._select_by_id_sql = select_by_id_sql
        self._select_all_sql = select_all_sql
        self._upsert_sql = upsert_sql
        self._delete_sql = delete_sql

    def find_by_id(self, entity_id: str) -> T | None:
        with self.db.connect() as conn:
            row = conn.execute(
                self._select_by_id_sql,
                (entity_id,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_entity(conn, row)

    def find_all(self) -> list[T]:
        with self.db.connect() as conn:
            rows = conn.execute(self._select_all_sql).fetchall()

            return [self._row_to_entity(conn, row) for row in rows]

    def save(self, entity: T) -> T:
        record = self._entity_to_record(entity)
        entity_id = str(record[self.id_column])

        with self.db.connect() as conn:
            conn.execute(
                self._upsert_sql,
                tuple(record[column] for column in self._write_columns),
            )
            self._after_save(conn, entity)
            conn.commit()

        saved = self.find_by_id(entity_id)
        if saved is None:
            raise RuntimeError(f"Saved entity {entity_id} could not be reloaded.")
        return saved

    def delete(self, entity_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute(self._delete_sql, (entity_id,))
            conn.commit()

    @abstractmethod
    def _entity_to_record(self, entity: T) -> dict[str, Any]:
        """Serialize an entity into table columns."""

    @abstractmethod
    def _row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> T:
        """Convert a database row into the typed entity."""

    def _after_save(self, conn: sqlite3.Connection, entity: T) -> None:
        """Hook for repositories that need secondary table writes."""


class ExecutableRepository(Repository[ExecutableIdentity]):
    def __init__(self, db: Database) -> None:
        super().__init__(
            db=db,
            id_column="exe_id",
            write_columns=(
                "exe_id",
                "normalized_key",
                "path",
                "filename",
                "original_filename",
                "product_name",
                "file_description",
                "signer",
                "company_name",
                "sha1",
                "classification",
                "classification_confidence",
                "ignored",
                "first_seen",
                "last_seen",
            ),
            select_by_id_sql="SELECT * FROM executables WHERE exe_id = ?",
            select_all_sql="SELECT * FROM executables ORDER BY exe_id ASC",
            upsert_sql="""
                INSERT INTO executables (
                    exe_id, normalized_key, path, filename, original_filename, product_name,
                    file_description, signer, company_name, sha1, classification,
                    classification_confidence, ignored, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exe_id) DO UPDATE SET
                    normalized_key = excluded.normalized_key,
                    path = excluded.path,
                    filename = excluded.filename,
                    original_filename = excluded.original_filename,
                    product_name = excluded.product_name,
                    file_description = excluded.file_description,
                    signer = excluded.signer,
                    company_name = excluded.company_name,
                    sha1 = excluded.sha1,
                    classification = excluded.classification,
                    classification_confidence = excluded.classification_confidence,
                    ignored = excluded.ignored,
                    first_seen = excluded.first_seen,
                    last_seen = excluded.last_seen
            """,
            delete_sql="DELETE FROM executables WHERE exe_id = ?",
        )

    def find_by_normalized_key(self, key: str) -> ExecutableIdentity | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM executables WHERE normalized_key = ?",
                (key,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_entity(conn, row)

    def _entity_to_record(self, entity: ExecutableIdentity) -> dict[str, Any]:
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
            "first_seen": _serialize_datetime(entity.first_seen),
            "last_seen": _serialize_datetime(entity.last_seen),
        }

    def _row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> ExecutableIdentity:
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
            classification=Classification(row["classification"]),
            classification_confidence=ConfidenceLevel(row["classification_confidence"]),
            ignored=bool(row["ignored"]),
            first_seen=_parse_datetime(row["first_seen"]),
            last_seen=_parse_datetime(row["last_seen"]),
        )


class SessionRepository(Repository[SessionRecord]):
    def __init__(self, db: Database) -> None:
        super().__init__(
            db=db,
            id_column="session_id",
            write_columns=(
                "session_id",
                "title_id",
                "exe_id",
                "user_sid",
                "started_at",
                "ended_at",
                "duration_seconds",
                "foreground_seconds",
                "bytes_in",
                "bytes_out",
                "confidence",
                "evidence_sources",
                "evidence_ids",
                "parent_chain",
                "notes",
            ),
            select_by_id_sql="SELECT * FROM sessions WHERE session_id = ?",
            select_all_sql="SELECT * FROM sessions ORDER BY session_id ASC",
            upsert_sql="""
                INSERT INTO sessions (
                    session_id, title_id, exe_id, user_sid, started_at, ended_at,
                    duration_seconds, foreground_seconds, bytes_in, bytes_out,
                    confidence, evidence_sources, evidence_ids, parent_chain, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title_id = excluded.title_id,
                    exe_id = excluded.exe_id,
                    user_sid = excluded.user_sid,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    duration_seconds = excluded.duration_seconds,
                    foreground_seconds = excluded.foreground_seconds,
                    bytes_in = excluded.bytes_in,
                    bytes_out = excluded.bytes_out,
                    confidence = excluded.confidence,
                    evidence_sources = excluded.evidence_sources,
                    evidence_ids = excluded.evidence_ids,
                    parent_chain = excluded.parent_chain,
                    notes = excluded.notes
            """,
            delete_sql="DELETE FROM sessions WHERE session_id = ?",
        )

    def find_by_exe_id(self, exe_id: str) -> list[SessionRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM sessions
                WHERE exe_id = ?
                ORDER BY started_at ASC, session_id ASC
                """,
                (exe_id,),
            ).fetchall()

            return [self._row_to_entity(conn, row) for row in rows]

    def _entity_to_record(self, entity: SessionRecord) -> dict[str, Any]:
        return {
            "session_id": entity.session_id,
            "title_id": entity.title_id,
            "exe_id": entity.exe_id,
            "user_sid": entity.user_sid,
            "started_at": _serialize_datetime(entity.started_at),
            "ended_at": _serialize_datetime(entity.ended_at),
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

    def _row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            title_id=row["title_id"],
            exe_id=row["exe_id"],
            user_sid=row["user_sid"],
            started_at=_parse_datetime(row["started_at"]),
            ended_at=_parse_datetime(row["ended_at"]),
            duration_seconds=row["duration_seconds"],
            foreground_seconds=int(row["foreground_seconds"]),
            bytes_in=int(row["bytes_in"]),
            bytes_out=int(row["bytes_out"]),
            confidence=RuntimeConfidence(row["confidence"]),
            evidence_sources=_load_json_list(row["evidence_sources"]),
            evidence_ids=_load_json_list(row["evidence_ids"]),
            parent_chain=_load_json_list(row["parent_chain"]),
            notes=_load_json_list(row["notes"]),
        )


class TitleRepository(Repository[TitleAggregate]):
    def __init__(self, db: Database) -> None:
        super().__init__(
            db=db,
            id_column="title_id",
            write_columns=(
                "title_id",
                "title",
                "classification",
                "classification_confidence",
                "title_confidence",
                "launcher",
                "confirmed_seconds",
                "estimated_seconds",
                "foreground_seconds",
                "runtime_confidence",
                "launches_confirmed",
                "launches_inferred",
                "launches_gui",
                "launches_confidence",
                "first_seen",
                "last_seen",
                "evidence_sources",
                "tags",
                "notes",
            ),
            select_by_id_sql="SELECT * FROM titles WHERE title_id = ?",
            select_all_sql="SELECT * FROM titles ORDER BY title_id ASC",
            upsert_sql="""
                INSERT INTO titles (
                    title_id, title, classification, classification_confidence, title_confidence,
                    launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                    runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                    launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title_id) DO UPDATE SET
                    title = excluded.title,
                    classification = excluded.classification,
                    classification_confidence = excluded.classification_confidence,
                    title_confidence = excluded.title_confidence,
                    launcher = excluded.launcher,
                    confirmed_seconds = excluded.confirmed_seconds,
                    estimated_seconds = excluded.estimated_seconds,
                    foreground_seconds = excluded.foreground_seconds,
                    runtime_confidence = excluded.runtime_confidence,
                    launches_confirmed = excluded.launches_confirmed,
                    launches_inferred = excluded.launches_inferred,
                    launches_gui = excluded.launches_gui,
                    launches_confidence = excluded.launches_confidence,
                    first_seen = excluded.first_seen,
                    last_seen = excluded.last_seen,
                    evidence_sources = excluded.evidence_sources,
                    tags = excluded.tags,
                    notes = excluded.notes
            """,
            delete_sql="DELETE FROM titles WHERE title_id = ?",
        )

    def find_by_classification(self, classification: Classification) -> list[TitleAggregate]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM titles
                WHERE classification = ?
                ORDER BY title ASC, title_id ASC
                """,
                (classification.value,),
            ).fetchall()

            return [self._row_to_entity(conn, row) for row in rows]

    def _entity_to_record(self, entity: TitleAggregate) -> dict[str, Any]:
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
            "first_seen": _serialize_datetime(entity.first_seen),
            "last_seen": _serialize_datetime(entity.last_seen),
            "evidence_sources": json.dumps(entity.evidence_sources),
            "tags": json.dumps(entity.tags),
            "notes": json.dumps(entity.notes),
        }

    def _row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> TitleAggregate:
        executable_rows = conn.execute(
            """
            SELECT exe_id
            FROM title_executables
            WHERE title_id = ?
            ORDER BY exe_id ASC
            """,
            (row["title_id"],),
        ).fetchall()

        return TitleAggregate(
            title_id=row["title_id"],
            title=row["title"],
            classification=Classification(row["classification"]),
            classification_confidence=ConfidenceLevel(row["classification_confidence"]),
            title_confidence=ConfidenceLevel(row["title_confidence"]),
            launcher=row["launcher"],
            runtime=RuntimeStats(
                confirmed_seconds=int(row["confirmed_seconds"]),
                estimated_seconds=int(row["estimated_seconds"]),
                foreground_seconds=int(row["foreground_seconds"]),
                confidence=ConfidenceLevel(row["runtime_confidence"]),
            ),
            launches=LaunchStats(
                confirmed=int(row["launches_confirmed"]),
                inferred=int(row["launches_inferred"]),
                gui=int(row["launches_gui"]),
                confidence=ConfidenceLevel(row["launches_confidence"]),
            ),
            first_seen=_parse_datetime(row["first_seen"]),
            last_seen=_parse_datetime(row["last_seen"]),
            executable_ids=[record["exe_id"] for record in executable_rows],
            evidence_sources=_load_json_list(row["evidence_sources"]),
            tags=_load_json_list(row["tags"]),
            notes=_load_json_list(row["notes"]),
        )

    def _after_save(self, conn: sqlite3.Connection, entity: TitleAggregate) -> None:
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
    def __init__(self, db: Database) -> None:
        super().__init__(
            db=db,
            id_column="mapping_id",
            write_columns=(
                "mapping_id",
                "target",
                "title",
                "classification",
                "launcher",
                "ignore",
                "created_at",
                "confidence",
            ),
            select_by_id_sql="SELECT * FROM mappings WHERE mapping_id = ?",
            select_all_sql="SELECT * FROM mappings ORDER BY mapping_id ASC",
            upsert_sql="""
                INSERT INTO mappings (
                    mapping_id, target, title, classification, launcher,
                    ignore, created_at, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mapping_id) DO UPDATE SET
                    target = excluded.target,
                    title = excluded.title,
                    classification = excluded.classification,
                    launcher = excluded.launcher,
                    ignore = excluded.ignore,
                    created_at = excluded.created_at,
                    confidence = excluded.confidence
            """,
            delete_sql="DELETE FROM mappings WHERE mapping_id = ?",
        )
        self._normalizer = IdentityNormalizer()

    def find_by_target(self, target: str) -> UserMapping | None:
        candidates = self._target_candidates(target)

        with self.db.connect() as conn:
            for candidate in candidates:
                row = conn.execute(
                    "SELECT * FROM mappings WHERE target = ?",
                    (candidate,),
                ).fetchone()
                if row is not None:
                    return self._row_to_entity(conn, row)

        return None

    def _entity_to_record(self, entity: UserMapping) -> dict[str, Any]:
        normalized_target = self._normalizer.normalize_executable_target(entity.target)
        stored_target = normalized_target or entity.target.strip()

        return {
            "mapping_id": entity.mapping_id,
            "target": stored_target,
            "title": entity.title,
            "classification": entity.classification.value if entity.classification else None,
            "launcher": entity.launcher,
            "ignore": 1 if entity.ignore else 0,
            "created_at": _serialize_datetime(entity.created_at),
            "confidence": entity.confidence.value,
        }

    def _row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> UserMapping:
        target = row["target"]
        return UserMapping(
            mapping_id=row["mapping_id"],
            target=target,
            title=row["title"],
            classification=_optional_enum(Classification, row["classification"]),
            launcher=row["launcher"],
            ignore=bool(row["ignore"]),
            created_at=_parse_datetime(row["created_at"]) or Clock.utc_now(),
            normalized_key=self._normalizer.normalize_executable_target(target),
            confidence=_optional_enum(ConfidenceLevel, row["confidence"], ConfidenceLevel.HIGH)
            or ConfidenceLevel.HIGH,
        )

    def _target_candidates(self, target: str) -> list[str]:
        stripped = target.strip()
        normalized = self._normalizer.normalize_executable_target(stripped)

        candidates: list[str] = []
        for candidate in (stripped, normalized):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        return candidates


def _parse_datetime(value: str | None) -> datetime | None:
    return Clock.parse_iso8601(value)


def _serialize_datetime(value: datetime | None) -> str | None:
    return Clock.format_iso8601(value)


def _load_json_list(value: str) -> list[str]:
    return list(json.loads(value))


def _optional_enum(
    enum_type: type[EnumT],
    value: str | None,
    default: EnumT | None = None,
) -> EnumT | None:
    if not value:
        return default
    try:
        return enum_type(value)
    except ValueError:
        return default
