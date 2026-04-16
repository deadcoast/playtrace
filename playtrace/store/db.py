from __future__ import annotations

import json
import socket
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import (
    Classification,
    ConfidenceLevel,
    EvidenceStrength,
    EvidenceType,
    RuntimeConfidence,
    SourceName,
)
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.report import CoverageSummary, ReportSnapshot
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.schema import SCHEMA_SQL

EnumT = TypeVar("EnumT", bound=Enum)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def bootstrap(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def create_scan_run(self, selected_sources: list[str]) -> str:
        scan_run_id = f"scan:{uuid4().hex}"
        started_at = self._utc_now().isoformat()
        host_name = socket.gethostname()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO scan_runs (
                    scan_run_id, started_at, finished_at, host_name, selected_sources, warnings
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_run_id,
                    started_at,
                    None,
                    host_name,
                    json.dumps(selected_sources),
                    json.dumps([]),
                ),
            )
            conn.commit()

        return scan_run_id

    def finish_scan_run(self, scan_run_id: str, warnings: list[str]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET finished_at = ?, warnings = ?
                WHERE scan_run_id = ?
                """,
                (
                    self._utc_now().isoformat(),
                    json.dumps(warnings),
                    scan_run_id,
                ),
            )
            conn.commit()

    def replace_artifacts_for_scan(self, scan_run_id: str, artifacts: list[RawArtifact]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM artifacts WHERE scan_run_id = ?", (scan_run_id,))
            conn.executemany(
                """
                INSERT INTO artifacts (
                    artifact_id, scan_run_id, source, observed_at, raw_ref, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        artifact.artifact_id,
                        scan_run_id,
                        artifact.source.value,
                        artifact.observed_at.isoformat() if artifact.observed_at else None,
                        artifact.raw_ref,
                        json.dumps(artifact.payload),
                    )
                    for artifact in artifacts
                ],
            )
            conn.commit()

    def replace_evidence_for_scan(self, scan_run_id: str, records: list[EvidenceRecord]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM evidence_links WHERE scan_run_id = ?", (scan_run_id,))
            conn.executemany(
                """
                INSERT INTO evidence_links (
                    evidence_id, scan_run_id, artifact_id, source, evidence_type,
                    observed_at, strength, value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.evidence_id,
                        scan_run_id,
                        record.artifact_id,
                        record.source.value,
                        record.evidence_type.value,
                        record.observed_at.isoformat() if record.observed_at else None,
                        record.strength.value,
                        json.dumps(record.value),
                    )
                    for record in records
                ],
            )
            conn.commit()

    def load_evidence_records(self) -> list[EvidenceRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT evidence_id, artifact_id, source, evidence_type, observed_at, strength, value
                FROM evidence_links
                ORDER BY observed_at ASC, evidence_id ASC
                """
            ).fetchall()

        records: list[EvidenceRecord] = []
        for row in rows:
            records.append(
                EvidenceRecord(
                    evidence_id=row["evidence_id"],
                    artifact_id=row["artifact_id"],
                    source=SourceName(row["source"]),
                    evidence_type=EvidenceType(row["evidence_type"]),
                    observed_at=datetime.fromisoformat(row["observed_at"]) if row["observed_at"] else None,
                    strength=EvidenceStrength(row["strength"]),
                    value=json.loads(row["value"]),
                )
            )
        return records

    def load_user_mappings(self) -> list[UserMapping]:
        normalizer = IdentityNormalizer()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT mapping_id, target, title, classification, launcher, ignore, created_at, confidence
                FROM mappings
                ORDER BY created_at ASC
                """
            ).fetchall()

        mappings: list[UserMapping] = []
        for row in rows:
            classification = self._optional_enum(Classification, row["classification"])
            confidence = self._optional_enum(ConfidenceLevel, row["confidence"]) or ConfidenceLevel.HIGH
            mappings.append(
                UserMapping(
                    mapping_id=row["mapping_id"],
                    target=row["target"],
                    title=row["title"],
                    classification=classification,
                    launcher=row["launcher"],
                    ignore=bool(row["ignore"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    normalized_key=normalizer.normalize_executable_target(row["target"]),
                    confidence=confidence,
                )
            )
        return mappings

    def replace_executables(self, executables: list) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM executables")
            conn.executemany(
                """
                INSERT INTO executables (
                    exe_id, normalized_key, path, filename, original_filename, product_name,
                    file_description, signer, company_name, sha1, classification,
                    classification_confidence, ignored, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        executable.exe_id,
                        executable.normalized_key,
                        executable.canonical_path or executable.path,
                        executable.filename,
                        executable.original_filename,
                        executable.product_name,
                        executable.file_description,
                        executable.signer,
                        executable.company_name,
                        executable.sha1,
                        executable.classification.value,
                        executable.classification_confidence.value,
                        1 if executable.ignored else 0,
                        executable.first_seen.isoformat() if executable.first_seen else None,
                        executable.last_seen.isoformat() if executable.last_seen else None,
                    )
                    for executable in executables
                ],
            )
            conn.commit()

    def replace_sessions(self, sessions: list[SessionRecord]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions")
            conn.executemany(
                """
                INSERT INTO sessions (
                    session_id, title_id, exe_id, user_sid, started_at, ended_at,
                    duration_seconds, foreground_seconds, bytes_in, bytes_out,
                    confidence, evidence_sources, evidence_ids, parent_chain, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session.session_id,
                        session.title_id,
                        session.exe_id,
                        session.user_sid,
                        session.started_at.isoformat() if session.started_at else None,
                        session.ended_at.isoformat() if session.ended_at else None,
                        session.duration_seconds,
                        session.foreground_seconds,
                        session.bytes_in,
                        session.bytes_out,
                        session.confidence.value,
                        json.dumps(session.evidence_sources),
                        json.dumps(session.evidence_ids),
                        json.dumps(session.parent_chain),
                        json.dumps(session.notes),
                    )
                    for session in sessions
                ],
            )
            conn.commit()

    def replace_titles(self, titles: list[TitleAggregate]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM title_executables")
            conn.execute("DELETE FROM titles")
            conn.executemany(
                """
                INSERT INTO titles (
                    title_id, title, classification, classification_confidence, title_confidence,
                    launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                    runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                    launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        title.title_id,
                        title.title,
                        title.classification.value,
                        title.classification_confidence.value,
                        title.title_confidence.value,
                        title.launcher,
                        title.runtime.confirmed_seconds,
                        title.runtime.estimated_seconds,
                        title.runtime.foreground_seconds,
                        title.runtime.confidence.value,
                        title.launches.confirmed,
                        title.launches.inferred,
                        title.launches.gui,
                        title.launches.confidence.value,
                        title.first_seen.isoformat() if title.first_seen else None,
                        title.last_seen.isoformat() if title.last_seen else None,
                        json.dumps(title.evidence_sources),
                        json.dumps(title.tags),
                        json.dumps(title.notes),
                    )
                    for title in titles
                ],
            )
            conn.executemany(
                """
                INSERT INTO title_executables (title_id, exe_id)
                VALUES (?, ?)
                """,
                [
                    (title.title_id, exe_id)
                    for title in titles
                    for exe_id in title.executable_ids
                ],
            )
            conn.commit()

    def rebuild_from_artifacts_and_mappings(self) -> None:
        from playtrace.merge.sessions import SessionMerger
        from playtrace.merge.titles import TitleAggregator
        from playtrace.normalize.identity import IdentityNormalizer

        evidence = self.load_evidence_records()
        normalizer = IdentityNormalizer()
        executable_map: dict[str, ExecutableIdentity] = {}

        for record in evidence:
            executable = normalizer.to_executable(record)
            existing = executable_map.get(executable.exe_id)
            if existing is None:
                executable_map[executable.exe_id] = executable
                continue

            if not existing.path and executable.path:
                existing.path = executable.path
            if not existing.filename and executable.filename:
                existing.filename = executable.filename
            if not existing.product_name and executable.product_name:
                existing.product_name = executable.product_name
            if not existing.original_filename and executable.original_filename:
                existing.original_filename = executable.original_filename
            if not existing.company_name and executable.company_name:
                existing.company_name = executable.company_name
            if not existing.file_description and executable.file_description:
                existing.file_description = executable.file_description
            if not existing.sha1 and executable.sha1:
                existing.sha1 = executable.sha1
            if not existing.canonical_path and executable.canonical_path:
                existing.canonical_path = executable.canonical_path

        sessions = SessionMerger(normalizer=normalizer).build_sessions(evidence)
        titles = TitleAggregator().build(
            list(executable_map.values()),
            sessions,
            self.load_user_mappings(),
        )

        self.replace_executables(list(executable_map.values()))
        self.replace_sessions(sessions)
        self.replace_titles(titles)

    def seed_demo_data(self) -> None:
        with self.connect() as conn:
            title_count = conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
            if title_count:
                return

            now = self._utc_now()
            rows = [
                (
                    "title:elden_ring",
                    "Elden Ring",
                    "game",
                    "high",
                    "high",
                    "Steam",
                    152280,
                    0,
                    40020,
                    "high",
                    27,
                    7,
                    19,
                    "high",
                    (now - timedelta(days=120)).isoformat(),
                    (now - timedelta(days=3)).isoformat(),
                    json.dumps(["security_log", "prefetch", "userassist", "srum"]),
                    json.dumps(["soulslike"]),
                    json.dumps([]),
                ),
                (
                    "title:hades",
                    "Hades",
                    "game",
                    "high",
                    "high",
                    "Steam",
                    111900,
                    0,
                    28000,
                    "high",
                    44,
                    0,
                    31,
                    "high",
                    (now - timedelta(days=240)).isoformat(),
                    (now - timedelta(days=10)).isoformat(),
                    json.dumps(["prefetch", "userassist"]),
                    json.dumps(["roguelike"]),
                    json.dumps([]),
                ),
                (
                    "title:balatro",
                    "Balatro",
                    "game",
                    "medium",
                    "medium",
                    "Steam",
                    0,
                    65460,
                    9000,
                    "medium",
                    0,
                    63,
                    18,
                    "medium",
                    (now - timedelta(days=60)).isoformat(),
                    (now - timedelta(days=1)).isoformat(),
                    json.dumps(["prefetch", "userassist", "srum"]),
                    json.dumps(["deckbuilder"]),
                    json.dumps([]),
                ),
            ]
            conn.executemany(
                """
                INSERT INTO titles (
                    title_id, title, classification, classification_confidence, title_confidence,
                    launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                    runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                    launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    def load_evidence_inventory(self) -> tuple[set[str], set[str]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT source, evidence_type
                FROM evidence_links
                """
            ).fetchall()

        sources = {str(row["source"]) for row in rows}
        evidence_types = {str(row["evidence_type"]) for row in rows}
        return sources, evidence_types

    def count_sessions(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS session_count FROM sessions").fetchone()
        return int(row["session_count"] or 0)

    def count_duplicate_title_groups(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS duplicate_groups
                FROM (
                    SELECT LOWER(title) AS normalized_title
                    FROM titles
                    GROUP BY LOWER(title)
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()
        return int(row["duplicate_groups"] or 0)

    def count_unmapped_executables(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS unmapped_executables
                FROM executables
                LEFT JOIN title_executables
                  ON title_executables.exe_id = executables.exe_id
                WHERE title_executables.title_id IS NULL
                  AND executables.ignored = 0
                """
            ).fetchone()
        return int(row["unmapped_executables"] or 0)

    def load_titles(
        self,
        *,
        sort_by: str,
        classification: str | None,
        launcher: str | None,
        limit: int,
    ) -> list[TitleAggregate]:
        filters: list[str] = []
        params: list[object] = []
        if classification:
            filters.append("classification = ?")
            params.append(classification.lower())
        if launcher:
            filters.append("LOWER(COALESCE(launcher, '')) = ?")
            params.append(launcher.lower())

        order_by = {
            "runtime": "(confirmed_seconds + estimated_seconds) DESC, title ASC",
            "launches": "(launches_confirmed + launches_inferred) DESC, title ASC",
            "last_seen": "last_seen DESC, title ASC",
            "title": "title ASC",
        }.get(sort_by, "(confirmed_seconds + estimated_seconds) DESC, title ASC")

        query = "SELECT * FROM titles"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += f" ORDER BY {order_by} LIMIT ?"
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [self._title_from_row(row) for row in rows]

    def load_sessions(
        self,
        *,
        title: str | None,
        days: int,
        limit: int,
    ) -> list[tuple[str, SessionRecord]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filters = ["COALESCE(sessions.ended_at, sessions.started_at) >= ?"]
        params: list[object] = [cutoff.isoformat()]
        if title:
            filters.append("LOWER(COALESCE(titles.title, sessions.title_id, sessions.exe_id)) LIKE ?")
            params.append(f"%{title.lower()}%")

        query = f"""
            SELECT
                sessions.*,
                titles.title AS resolved_title
            FROM sessions
            LEFT JOIN titles ON titles.title_id = sessions.title_id
            WHERE {' AND '.join(filters)}
            ORDER BY COALESCE(sessions.ended_at, sessions.started_at) DESC, sessions.session_id DESC
            LIMIT ?
        """
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [
            (
                row["resolved_title"] or row["title_id"] or row["exe_id"],
                self._session_from_row(row),
            )
            for row in rows
        ]

    def load_snapshot(self, limit: int) -> ReportSnapshot:
        with self.connect() as conn:
            title_rows = conn.execute(
                """
                SELECT *
                FROM titles
                ORDER BY (confirmed_seconds + estimated_seconds) DESC, title ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            total_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS tracked_titles,
                    COALESCE(SUM(confirmed_seconds), 0) AS confirmed_runtime_seconds,
                    COALESCE(SUM(estimated_seconds), 0) AS estimated_runtime_seconds,
                    COALESCE(SUM(launches_confirmed), 0) AS confirmed_sessions
                FROM titles
                """
            ).fetchone()
            recent_session_rows = conn.execute(
                """
                SELECT
                    sessions.*,
                    titles.title AS resolved_title
                FROM sessions
                LEFT JOIN titles ON titles.title_id = sessions.title_id
                ORDER BY COALESCE(sessions.ended_at, sessions.started_at) DESC, sessions.session_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        titles = [self._title_from_row(row) for row in title_rows]
        recent_sessions = [self._session_from_row(row) for row in recent_session_rows]
        recent_session_titles = [
            row["resolved_title"] or row["title_id"] or row["exe_id"]
            for row in recent_session_rows
        ]

        warnings: list[str] = []
        if int(total_row["tracked_titles"] or 0) == 0:
            warnings.append("No persisted titles found. Run `playtrace scan` to collect evidence.")

        return ReportSnapshot(
            generated_at=self._utc_now(),
            host_name=socket.gethostname(),
            coverage=CoverageSummary(
                tracked_titles=int(total_row["tracked_titles"] or 0),
                confirmed_runtime_seconds=int(total_row["confirmed_runtime_seconds"] or 0),
                estimated_runtime_seconds=int(total_row["estimated_runtime_seconds"] or 0),
                confirmed_sessions=int(total_row["confirmed_sessions"] or 0),
                unmapped_executables=self.count_unmapped_executables(),
            ),
            top_titles=titles,
            recent_sessions=recent_sessions,
            recent_session_titles=recent_session_titles,
            warnings=warnings,
        )

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

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

    def _title_from_row(self, row: sqlite3.Row) -> TitleAggregate:
        return TitleAggregate(
            title_id=row["title_id"],
            title=row["title"],
            classification=self._optional_enum(Classification, row["classification"]) or Classification.UNKNOWN,
            classification_confidence=self._optional_enum(ConfidenceLevel, row["classification_confidence"])
            or ConfidenceLevel.UNKNOWN,
            title_confidence=self._optional_enum(ConfidenceLevel, row["title_confidence"])
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
            first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
            evidence_sources=self._json_list(row["evidence_sources"]),
            tags=self._json_list(row["tags"]),
            notes=self._json_list(row["notes"]),
        )

    def _session_from_row(self, row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            title_id=row["title_id"],
            exe_id=row["exe_id"],
            user_sid=row["user_sid"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            duration_seconds=row["duration_seconds"],
            foreground_seconds=int(row["foreground_seconds"] or 0),
            bytes_in=int(row["bytes_in"] or 0),
            bytes_out=int(row["bytes_out"] or 0),
            confidence=self._optional_enum(RuntimeConfidence, row["confidence"]) or RuntimeConfidence.UNKNOWN,
            evidence_sources=self._json_list(row["evidence_sources"]),
            evidence_ids=self._json_list(row["evidence_ids"]),
            parent_chain=self._json_list(row["parent_chain"]),
            notes=self._json_list(row["notes"]),
        )

    def _json_list(self, value: str | None) -> list[str]:
        return json.loads(value or "[]")
