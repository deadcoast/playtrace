from __future__ import annotations

from difflib import SequenceMatcher
import json
import re
import socket
import sqlite3
from datetime import datetime, timedelta
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
from playtrace.models.report import CoverageSummary, DuplicateCandidate, ReportSnapshot
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.config.runtime import ReconstructionSettings
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.schema import SCHEMA_SQL
from playtrace.utils.clock import Clock

EnumT = TypeVar("EnumT", bound=Enum)
LEGACY_SAMPLE_RAW_REFS = {
    r"amcache:D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
    r"bam:D:\Games\Balatro\balatro.exe",
    "prefetch:ELDENRING.EXE",
    "security_log:4688:15320",
    "srum:application-resource-usage",
    r"userassist:C:\Program Files (x86)\Steam\steam.exe",
}


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
        started_at = self._format_dt(self._utc_now())
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
                    self._format_dt(self._utc_now()),
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
                        self._format_dt(artifact.observed_at),
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
                        self._format_dt(record.observed_at),
                        record.strength.value,
                        json.dumps(record.value),
                    )
                    for record in records
                ],
            )
            conn.commit()

    def purge_legacy_sample_scan_runs(self) -> int:
        with self.connect() as conn:
            scan_runs = conn.execute(
                "SELECT DISTINCT scan_run_id FROM artifacts ORDER BY scan_run_id ASC"
            ).fetchall()

            stale_scan_run_ids: list[str] = []
            for row in scan_runs:
                scan_run_id = str(row["scan_run_id"])
                raw_refs = {
                    artifact_row["raw_ref"]
                    for artifact_row in conn.execute(
                        "SELECT raw_ref FROM artifacts WHERE scan_run_id = ?",
                        (scan_run_id,),
                    ).fetchall()
                }
                if raw_refs == LEGACY_SAMPLE_RAW_REFS:
                    stale_scan_run_ids.append(scan_run_id)

            if not stale_scan_run_ids:
                return 0

            placeholders = ", ".join("?" for _ in stale_scan_run_ids)
            conn.execute(
                f"DELETE FROM evidence_links WHERE scan_run_id IN ({placeholders})",
                stale_scan_run_ids,
            )
            conn.execute(
                f"DELETE FROM artifacts WHERE scan_run_id IN ({placeholders})",
                stale_scan_run_ids,
            )
            conn.execute(
                f"DELETE FROM scan_runs WHERE scan_run_id IN ({placeholders})",
                stale_scan_run_ids,
            )
            conn.commit()

        return len(stale_scan_run_ids)

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
                    observed_at=self._parse_dt(row["observed_at"]),
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
                    created_at=self._parse_dt(row["created_at"]) or self._utc_now(),
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
                        self._format_dt(executable.first_seen),
                        self._format_dt(executable.last_seen),
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
                        self._format_dt(session.started_at),
                        self._format_dt(session.ended_at),
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
                        self._format_dt(title.first_seen),
                        self._format_dt(title.last_seen),
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

    def rebuild_from_artifacts_and_mappings(
        self,
        settings: ReconstructionSettings | None = None,
    ) -> None:
        executables, sessions, titles = self.build_reconstruction_state(settings=settings)
        self.replace_executables(executables)
        self.replace_sessions(sessions)
        self.replace_titles(titles)

    def build_reconstruction_state(
        self,
        settings: ReconstructionSettings | None = None,
    ) -> tuple[list[ExecutableIdentity], list[SessionRecord], list[TitleAggregate]]:
        from playtrace.merge.sessions import SessionMerger
        from playtrace.merge.sessions import SessionMergeConfig
        from playtrace.merge.titles import TitleAggregator
        from playtrace.normalize.identity import IdentityNormalizer

        settings = settings or ReconstructionSettings()
        evidence = self._filter_evidence_records(
            self.load_evidence_records(),
            minimum_confidence=settings.minimum_evidence_confidence,
        )
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

        sessions = SessionMerger(
            config=SessionMergeConfig(
                dedupe_window=timedelta(minutes=settings.session_merge_dedupe_window_minutes)
            ),
            normalizer=normalizer,
        ).build_sessions(evidence)
        titles = TitleAggregator().build(
            list(executable_map.values()),
            sessions,
            self.load_user_mappings(),
            evidence_records=evidence,
            config_overrides=settings.classification_overrides or {},
        )
        if settings.duplicate_auto_merge:
            titles = self._auto_merge_duplicate_titles(
                titles,
                threshold=settings.duplicate_similarity_threshold,
            )
        title_ids_by_executable = {
            exe_id: title.title_id
            for title in titles
            for exe_id in title.executable_ids
        }
        for session in sessions:
            session.title_id = title_ids_by_executable.get(session.exe_id)

        return list(executable_map.values()), sessions, titles

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
                    self._format_dt(now - timedelta(days=120)),
                    self._format_dt(now - timedelta(days=3)),
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
                    self._format_dt(now - timedelta(days=240)),
                    self._format_dt(now - timedelta(days=10)),
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
                    self._format_dt(now - timedelta(days=60)),
                    self._format_dt(now - timedelta(days=1)),
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

    def load_latest_scan_context(self) -> tuple[str | None, datetime | None]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    host_name,
                    COALESCE(finished_at, started_at) AS latest_at
                FROM scan_runs
                ORDER BY COALESCE(finished_at, started_at) DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None, None
        latest_at = self._parse_dt(row["latest_at"])
        return row["host_name"], latest_at

    def count_sessions(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS session_count FROM sessions").fetchone()
        return int(row["session_count"] or 0)

    def count_duplicate_title_groups(self) -> int:
        titles = self.load_titles(
            sort_by="runtime",
            classification=None,
            launcher=None,
            limit=10_000,
        )
        return len(self.duplicate_groups(titles, threshold=0.75))

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
            "launches": "(launches_confirmed + launches_inferred + launches_gui) DESC, title ASC",
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

    def load_duplicate_candidates(self) -> list[DuplicateCandidate]:
        titles = self.load_titles(
            sort_by="runtime",
            classification=None,
            launcher=None,
            limit=10_000,
        )
        candidates: list[DuplicateCandidate] = []
        for group in self.duplicate_groups(titles, threshold=0.75):
            primary = self._select_duplicate_primary(group)
            related = [title for title in group if title.title_id != primary.title_id]
            candidates.append(
                DuplicateCandidate(
                    primary_title_id=primary.title_id,
                    primary_title=primary.title,
                    related_title_ids=[title.title_id for title in related],
                    related_titles=[title.title for title in related],
                    reasons=["normalized title collision"],
                )
            )
        return candidates

    def duplicate_groups(
        self,
        titles: list[TitleAggregate],
        *,
        threshold: float,
    ) -> list[list[TitleAggregate]]:
        return self._duplicate_groups(titles, threshold=threshold)

    def load_executable_targets_for_titles(self, title_ids: list[str]) -> dict[str, list[str]]:
        if not title_ids:
            return {}

        placeholders = ", ".join("?" for _ in title_ids)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    title_executables.title_id,
                    COALESCE(executables.normalized_key, executables.exe_id) AS mapping_target
                FROM title_executables
                JOIN executables ON executables.exe_id = title_executables.exe_id
                WHERE title_executables.title_id IN ({placeholders})
                ORDER BY title_executables.title_id ASC, executables.exe_id ASC
                """,
                tuple(title_ids),
            ).fetchall()

        targets: dict[str, list[str]] = {title_id: [] for title_id in title_ids}
        for row in rows:
            targets.setdefault(row["title_id"], []).append(row["mapping_target"])
        return targets

    def find_lineage_title(
        self,
        target: str,
        normalized_target: str | None,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> sqlite3.Row | None:
        if conn is None:
            with self.connect() as local_conn:
                return self.find_lineage_title(target, normalized_target, conn=local_conn)

        return conn.execute(
            """
            SELECT DISTINCT titles.*
            FROM titles
            LEFT JOIN title_executables
              ON title_executables.title_id = titles.title_id
            LEFT JOIN sessions
              ON sessions.title_id = titles.title_id
            WHERE lower(titles.title) = lower(?)
               OR titles.title_id = ?
               OR title_executables.exe_id = ?
               OR sessions.exe_id = ?
            ORDER BY
              CASE COALESCE(titles.title_confidence, 'unknown')
                WHEN 'high' THEN 0
                WHEN 'medium' THEN 1
                WHEN 'low' THEN 2
                ELSE 3
              END ASC,
              (COALESCE(titles.confirmed_seconds, 0) + COALESCE(titles.estimated_seconds, 0)) DESC,
              lower(titles.title) ASC,
              titles.title_id ASC
            LIMIT 1
            """,
            (
                target,
                target,
                normalized_target or target,
                normalized_target or target,
            ),
        ).fetchone()

    def load_lineage_executables(
        self,
        *,
        title_id: str | None = None,
        normalized_target: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> list[sqlite3.Row]:
        if conn is None:
            with self.connect() as local_conn:
                return self.load_lineage_executables(
                    title_id=title_id,
                    normalized_target=normalized_target,
                    conn=local_conn,
                )

        clauses: list[str] = []
        params: list[object] = []

        if title_id:
            clauses.append("title_executables.title_id = ?")
            params.append(title_id)
        if normalized_target:
            clauses.append("executables.exe_id = ?")
            params.append(normalized_target)

        if not clauses:
            return []

        return conn.execute(
            f"""
            SELECT DISTINCT executables.*
            FROM executables
            LEFT JOIN title_executables
              ON title_executables.exe_id = executables.exe_id
            WHERE {' OR '.join(clauses)}
            ORDER BY executables.exe_id ASC
            """,
            tuple(params),
        ).fetchall()

    def load_lineage_evidence_rows(
        self,
        *,
        search_terms: list[str],
        conn: sqlite3.Connection | None = None,
    ) -> list[sqlite3.Row]:
        if not search_terms:
            return []
        if conn is None:
            with self.connect() as local_conn:
                return self.load_lineage_evidence_rows(search_terms=search_terms, conn=local_conn)

        clauses: list[str] = []
        params: list[object] = []
        for term in search_terms:
            like_term = f"%{term}%"
            clauses.append(
                """
                lower(COALESCE(artifacts.raw_ref, '')) LIKE ?
                OR lower(COALESCE(artifacts.payload, '')) LIKE ?
                OR lower(COALESCE(evidence_links.value, '')) LIKE ?
                """
            )
            params.extend([like_term, like_term, like_term])

        query = f"""
            SELECT
                artifacts.source AS artifact_source,
                artifacts.payload AS artifact_payload,
                artifacts.raw_ref AS raw_ref,
                evidence_links.evidence_id AS evidence_id,
                evidence_links.source AS evidence_source,
                evidence_links.evidence_type AS evidence_type,
                evidence_links.observed_at AS observed_at,
                evidence_links.strength AS strength,
                evidence_links.value AS evidence_value
            FROM artifacts
            LEFT JOIN evidence_links
              ON evidence_links.artifact_id = artifacts.artifact_id
            WHERE {' OR '.join(f'({clause.strip()})' for clause in clauses)}
            ORDER BY COALESCE(evidence_links.observed_at, artifacts.observed_at) DESC, artifacts.artifact_id DESC
        """
        return conn.execute(query, tuple(params)).fetchall()

    def load_sessions(
        self,
        *,
        title: str | None,
        days: int,
        limit: int,
    ) -> list[tuple[str, SessionRecord]]:
        cutoff = self._utc_now() - timedelta(days=days)
        filters = ["julianday(COALESCE(sessions.ended_at, sessions.started_at)) >= julianday(?)"]
        params: list[object] = [self._format_dt(cutoff)]
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
            ORDER BY julianday(COALESCE(sessions.ended_at, sessions.started_at)) DESC, sessions.session_id DESC
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
                    (SELECT COUNT(*) FROM sessions) AS confirmed_sessions
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
                ORDER BY julianday(COALESCE(sessions.ended_at, sessions.started_at)) DESC, sessions.session_id DESC
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
        return Clock.utc_now()

    def _format_dt(self, value: datetime | None) -> str | None:
        return Clock.format_iso8601(value)

    def _parse_dt(self, value: str | None) -> datetime | None:
        return Clock.parse_iso8601(value)

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
            first_seen=self._parse_dt(row["first_seen"]),
            last_seen=self._parse_dt(row["last_seen"]),
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
            started_at=self._parse_dt(row["started_at"]),
            ended_at=self._parse_dt(row["ended_at"]),
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

    def _normalized_title_key(self, title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", title.casefold())

    def _duplicate_similarity(self, left: str, right: str) -> float:
        left_key = self._normalized_title_key(left)
        right_key = self._normalized_title_key(right)
        if not left_key or not right_key:
            return 0.0
        return SequenceMatcher(a=left_key, b=right_key).ratio()

    def _duplicate_groups(
        self,
        titles: list[TitleAggregate],
        *,
        threshold: float,
    ) -> list[list[TitleAggregate]]:
        if len(titles) < 2:
            return []

        parent = list(range(len(titles)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(titles)):
            for right in range(left + 1, len(titles)):
                if self._duplicate_similarity(titles[left].title, titles[right].title) >= threshold:
                    union(left, right)

        grouped: dict[int, list[TitleAggregate]] = {}
        for index, title in enumerate(titles):
            grouped.setdefault(find(index), []).append(title)

        return [group for group in grouped.values() if len(group) > 1]

    def _select_duplicate_primary(self, group: list[TitleAggregate]) -> TitleAggregate:
        return sorted(
            group,
            key=lambda item: (
                self._title_confidence_rank(item.title_confidence),
                -(item.runtime.confirmed_seconds + item.runtime.estimated_seconds),
                item.title.casefold(),
            ),
        )[0]

    def _auto_merge_duplicate_titles(
        self,
        titles: list[TitleAggregate],
        *,
        threshold: float,
    ) -> list[TitleAggregate]:
        merged_titles: list[TitleAggregate] = []
        merged_ids: set[str] = set()
        for group in self._duplicate_groups(titles, threshold=threshold):
            primary = self._select_duplicate_primary(group)
            merged = primary
            for title in group:
                merged_ids.add(title.title_id)
                if title.title_id == primary.title_id:
                    continue
                merged.runtime.confirmed_seconds += title.runtime.confirmed_seconds
                merged.runtime.estimated_seconds += title.runtime.estimated_seconds
                merged.runtime.foreground_seconds += title.runtime.foreground_seconds
                merged.launches.confirmed += title.launches.confirmed
                merged.launches.inferred += title.launches.inferred
                merged.launches.gui += title.launches.gui
                merged.evidence_sources = sorted(set(merged.evidence_sources + title.evidence_sources))
                merged.executable_ids = list(dict.fromkeys(merged.executable_ids + title.executable_ids))
                merged.suppressed_executable_ids = list(
                    dict.fromkeys(
                        merged.suppressed_executable_ids + title.suppressed_executable_ids
                    )
                )
                if merged.first_seen is None or (
                    title.first_seen is not None and title.first_seen < merged.first_seen
                ):
                    merged.first_seen = title.first_seen
                if merged.last_seen is None or (
                    title.last_seen is not None and title.last_seen > merged.last_seen
                ):
                    merged.last_seen = title.last_seen
            merged_titles.append(merged)

        merged_titles.extend([title for title in titles if title.title_id not in merged_ids])
        return merged_titles

    def _filter_evidence_records(
        self,
        records: list[EvidenceRecord],
        *,
        minimum_confidence: str,
    ) -> list[EvidenceRecord]:
        threshold = {
            "low": 0,
            "medium": 1,
            "high": 2,
        }.get(minimum_confidence, 0)
        strength_rank = {
            EvidenceStrength.EXACT: 2,
            EvidenceStrength.STRONG: 2,
            EvidenceStrength.INTERACTIVE: 2,
            EvidenceStrength.ESTIMATED: 1,
            EvidenceStrength.WEAK: 0,
            EvidenceStrength.UNKNOWN: 0,
        }
        return [
            record
            for record in records
            if strength_rank.get(record.strength, 0) >= threshold
        ]

    def _title_confidence_rank(self, confidence: ConfidenceLevel) -> int:
        ranks = {
            ConfidenceLevel.HIGH: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.LOW: 2,
            ConfidenceLevel.UNKNOWN: 3,
        }
        return ranks.get(confidence, 99)
