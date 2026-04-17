from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from uuid import uuid4

from playtrace.models.enums import Classification
from playtrace.models.report import DuplicateCandidate
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.db import Database
from playtrace.utils.clock import Clock


@dataclass(slots=True)
class MapRequest:
    db_path: Path
    target: str | None = None
    title: str | None = None
    classification: Classification | None = None
    launcher: str | None = None
    ignore: bool = False
    auto: bool = False


class MapperService:
    def apply(self, request: MapRequest) -> int:
        if request.auto:
            return self.apply_auto_merge(request)

        if not request.target or not request.title:
            raise ValueError("Manual mappings require both target and title.")

        db = Database(request.db_path)
        db.bootstrap()
        with db.connect() as conn:
            self._store_mapping(
                conn=conn,
                target=request.target,
                title=request.title,
                classification=request.classification,
                launcher=request.launcher,
                ignore=request.ignore,
            )
        return 1

    def apply_auto_merge(self, request: MapRequest) -> int:
        db = Database(request.db_path)
        db.bootstrap()
        candidates = db.load_duplicate_candidates()
        if not candidates:
            return 0

        title_targets = db.load_executable_targets_for_titles(
            [title_id for candidate in candidates for title_id in candidate.related_title_ids]
        )

        for candidate in candidates:
            primary = self._primary_title(candidate)
            secondary_targets = []
            for title_id in candidate.related_title_ids:
                secondary_targets.extend(title_targets.get(title_id, []))

            with db.connect() as conn:
                for target in secondary_targets:
                    self._store_mapping(
                        conn=conn,
                        target=target,
                        title=primary.primary_title,
                        classification=None,
                        launcher=None,
                        ignore=False,
                    )

                self._merge_persisted_titles(conn=conn, candidate=primary)

        return len(candidates)

    def _primary_title(self, candidate: DuplicateCandidate) -> DuplicateCandidate:
        return candidate

    def _store_mapping(
        self,
        *,
        conn: sqlite3.Connection,
        target: str,
        title: str,
        classification: Classification | None,
        launcher: str | None,
        ignore: bool,
    ) -> None:
        normalizer = IdentityNormalizer()
        normalized_target = normalizer.normalize_executable_target(target)
        stored_target = normalized_target or target.strip()
        conn.execute("DELETE FROM mappings WHERE target = ?", (stored_target,))
        conn.execute(
            """
            INSERT INTO mappings (
                mapping_id, target, title, classification, launcher,
                ignore, created_at, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"mapping:{uuid4().hex}",
                stored_target,
                title,
                classification.value if classification else None,
                launcher,
                1 if ignore else 0,
                Clock.format_iso8601(Clock.utc_now()),
                "high",
            ),
        )

    def _merge_persisted_titles(self, *, conn: sqlite3.Connection, candidate: DuplicateCandidate) -> None:
        if not candidate.related_title_ids:
            return

        placeholders = ", ".join("?" for _ in candidate.related_title_ids)
        totals = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(confirmed_seconds), 0) AS confirmed_seconds,
                COALESCE(SUM(estimated_seconds), 0) AS estimated_seconds,
                COALESCE(SUM(foreground_seconds), 0) AS foreground_seconds,
                COALESCE(SUM(launches_confirmed), 0) AS launches_confirmed,
                COALESCE(SUM(launches_inferred), 0) AS launches_inferred,
                COALESCE(SUM(launches_gui), 0) AS launches_gui,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen
            FROM titles
            WHERE title_id IN ({placeholders})
            """,
            tuple(candidate.related_title_ids),
        ).fetchone()
        conn.execute(
            """
            UPDATE titles
            SET
                confirmed_seconds = confirmed_seconds + ?,
                estimated_seconds = estimated_seconds + ?,
                foreground_seconds = foreground_seconds + ?,
                launches_confirmed = launches_confirmed + ?,
                launches_inferred = launches_inferred + ?,
                launches_gui = launches_gui + ?,
                first_seen = COALESCE(MIN(first_seen, ?), ?, first_seen),
                last_seen = COALESCE(MAX(last_seen, ?), ?, last_seen)
            WHERE title_id = ?
            """,
            (
                int(totals["confirmed_seconds"] or 0),
                int(totals["estimated_seconds"] or 0),
                int(totals["foreground_seconds"] or 0),
                int(totals["launches_confirmed"] or 0),
                int(totals["launches_inferred"] or 0),
                int(totals["launches_gui"] or 0),
                totals["first_seen"],
                totals["first_seen"],
                totals["last_seen"],
                totals["last_seen"],
                candidate.primary_title_id,
            ),
        )
        conn.execute(
            f"""
            UPDATE title_executables
            SET title_id = ?
            WHERE title_id IN ({placeholders})
            """,
            (candidate.primary_title_id, *candidate.related_title_ids),
        )
        conn.execute(
            f"""
            UPDATE sessions
            SET title_id = ?
            WHERE title_id IN ({placeholders})
            """,
            (candidate.primary_title_id, *candidate.related_title_ids),
        )
        conn.execute(
            f"""
            DELETE FROM titles
            WHERE title_id IN ({placeholders})
            """,
            tuple(candidate.related_title_ids),
        )
