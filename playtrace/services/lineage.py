from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
import sqlite3

from playtrace.classify.heuristics import normalize_title
from playtrace.models.lineage import (
    EntityLineageSnapshot,
    LineageContribution,
    SourcesLineageSnapshot,
)
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.db import Database


class LineageService:
    def __init__(self, *, normalizer: IdentityNormalizer | None = None) -> None:
        self.normalizer = normalizer or IdentityNormalizer()

    def load_entity(self, db_path: Path, target: str) -> EntityLineageSnapshot:
        db = Database(db_path)
        db.bootstrap()
        normalized_target = self.normalizer.normalize_executable_target(target)

        with db.connect() as conn:
            title_row = self._find_title_row(conn, target, normalized_target)
            if title_row is None:
                sources_snapshot = self.load_sources(db_path, target)
                return EntityLineageSnapshot(
                    title=target,
                    runtime_confidence="unknown",
                    confidence_reasons=["No persisted title matched this target yet."],
                    contributions=sources_snapshot.contributions,
                    conflicts=sources_snapshot.conflicts,
                )

            executable_rows = self._load_executables(conn, title_id=str(title_row["title_id"]))
            evidence_rows = self._load_matching_evidence_rows(
                conn,
                target=target,
                normalized_target=normalized_target,
                title=str(title_row["title"]),
                executable_rows=executable_rows,
            )

        return EntityLineageSnapshot(
            title=str(title_row["title"]),
            runtime_confidence=str(title_row["runtime_confidence"] or "unknown"),
            confidence_reasons=self._build_entity_reasons(
                title_row=title_row,
                executable_rows=executable_rows,
                evidence_rows=evidence_rows,
            ),
            alternate_titles=self._alternate_titles(
                canonical_title=str(title_row["title"]),
                executable_rows=executable_rows,
            ),
            contributions=[self._to_contribution(row) for row in evidence_rows],
            conflicts=self._collect_conflicts(evidence_rows),
        )

    def load_sources(self, db_path: Path, target: str) -> SourcesLineageSnapshot:
        db = Database(db_path)
        db.bootstrap()
        normalized_target = self.normalizer.normalize_executable_target(target)

        with db.connect() as conn:
            title_row = self._find_title_row(conn, target, normalized_target)
            executable_rows = self._load_executables(
                conn,
                title_id=str(title_row["title_id"]) if title_row is not None else None,
                normalized_target=normalized_target,
            )
            evidence_rows = self._load_matching_evidence_rows(
                conn,
                target=target,
                normalized_target=normalized_target,
                title=str(title_row["title"]) if title_row is not None else None,
                executable_rows=executable_rows,
            )

        return SourcesLineageSnapshot(
            target=target,
            contributions=[self._to_contribution(row) for row in evidence_rows],
            conflicts=self._collect_conflicts(evidence_rows),
        )

    def _find_title_row(
        self,
        conn: sqlite3.Connection,
        target: str,
        normalized_target: str | None,
    ) -> sqlite3.Row | None:
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
            LIMIT 1
            """,
            (
                target,
                target,
                normalized_target or target,
                normalized_target or target,
            ),
        ).fetchone()

    def _load_executables(
        self,
        conn: sqlite3.Connection,
        *,
        title_id: str | None = None,
        normalized_target: str | None = None,
    ) -> list[sqlite3.Row]:
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

    def _load_matching_evidence_rows(
        self,
        conn: sqlite3.Connection,
        *,
        target: str,
        normalized_target: str | None,
        title: str | None,
        executable_rows: list[sqlite3.Row],
    ) -> list[sqlite3.Row]:
        rows = conn.execute(
            """
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
            ORDER BY COALESCE(evidence_links.observed_at, artifacts.observed_at) DESC, artifacts.artifact_id DESC
            """
        ).fetchall()

        search_terms = self._search_terms(
            target=target,
            normalized_target=normalized_target,
            title=title,
            executable_rows=executable_rows,
        )
        matched: list[sqlite3.Row] = []
        for row in rows:
            if self._matches_row(row, search_terms):
                matched.append(row)
        return matched

    def _search_terms(
        self,
        *,
        target: str,
        normalized_target: str | None,
        title: str | None,
        executable_rows: list[sqlite3.Row],
    ) -> list[str]:
        terms: list[str] = []

        def add_term(value: str | None, *, as_path: bool = False, as_filename: bool = False) -> None:
            if not value:
                return
            text = str(value).strip().lower()
            if not text:
                return
            if text not in terms:
                terms.append(text)
            normalized_text = text.replace("\\\\", "\\")
            if normalized_text not in terms:
                terms.append(normalized_text)
            if as_path or as_filename:
                name = PureWindowsPath(text).name
                if name and name not in terms:
                    terms.append(name)

        add_term(target, as_path=True, as_filename=True)
        if normalized_target:
            add_term(normalized_target)
            if normalized_target.startswith("path:"):
                add_term(normalized_target[5:], as_path=True, as_filename=True)
        add_term(title)

        for row in executable_rows:
            add_term(row["exe_id"])
            add_term(row["path"], as_path=True, as_filename=True)
            add_term(row["normalized_key"])
            add_term(row["filename"], as_filename=True)
            add_term(row["original_filename"], as_filename=True)
            add_term(row["product_name"])
            add_term(row["file_description"])

        return terms

    def _matches_row(self, row: sqlite3.Row, search_terms: list[str]) -> bool:
        artifact_payload = self._json_object(row["artifact_payload"])
        evidence_value = self._json_object(row["evidence_value"])
        haystacks = [
            str(row["raw_ref"] or "").lower(),
            json.dumps(artifact_payload, sort_keys=True).lower(),
            json.dumps(evidence_value, sort_keys=True).lower(),
        ]
        haystacks.extend(haystack.replace("\\\\", "\\") for haystack in list(haystacks))
        return any(term in haystack for term in search_terms for haystack in haystacks if term)

    def _build_entity_reasons(
        self,
        *,
        title_row: sqlite3.Row,
        executable_rows: list[sqlite3.Row],
        evidence_rows: list[sqlite3.Row],
    ) -> list[str]:
        reasons: list[str] = []
        runtime_confidence = str(title_row["runtime_confidence"] or "unknown")
        if runtime_confidence == "exact":
            reasons.append("Exact runtime is available from matched session evidence.")
        elif runtime_confidence == "estimated":
            reasons.append("Runtime is estimated from supporting evidence rather than exact exits.")
        else:
            reasons.append("Runtime remains unknown because exact session evidence is incomplete.")

        if executable_rows:
            reasons.append(
                f"Canonical title is linked to {len(executable_rows)} executable record"
                f"{'' if len(executable_rows) == 1 else 's'}."
            )

        sources = sorted(
            {
                str(row["evidence_source"] or row["artifact_source"])
                for row in evidence_rows
                if row["evidence_source"] or row["artifact_source"]
            }
        )
        if sources:
            reasons.append(f"Evidence contributions currently come from: {', '.join(sources)}.")
        else:
            reasons.append("No source contributions are currently linked to this title.")

        return reasons

    def _alternate_titles(
        self,
        *,
        canonical_title: str,
        executable_rows: list[sqlite3.Row],
    ) -> list[str]:
        canonical_key = self._display_key(canonical_title)
        alternate_titles: list[str] = []
        seen: set[str] = set()

        for row in executable_rows:
            for candidate in (
                row["product_name"],
                row["file_description"],
                self._stem(row["original_filename"]),
                self._stem(row["filename"]),
            ):
                if not candidate:
                    continue
                normalized_candidate = self._display_key(str(candidate))
                if (
                    not normalized_candidate
                    or normalized_candidate == canonical_key
                    or normalized_candidate in seen
                ):
                    continue
                alternate_titles.append(str(candidate))
                seen.add(normalized_candidate)

        return alternate_titles

    def _collect_conflicts(self, evidence_rows: list[sqlite3.Row]) -> list[str]:
        hints_by_key: dict[str, str] = {}
        for row in evidence_rows:
            evidence_value = self._json_object(row["evidence_value"])
            artifact_payload = self._json_object(row["artifact_payload"])
            for candidate in (
                evidence_value.get("title_hint"),
                artifact_payload.get("title_hint"),
            ):
                if not candidate:
                    continue
                normalized_candidate = normalize_title(str(candidate))
                if normalized_candidate:
                    hints_by_key.setdefault(normalized_candidate, str(candidate))

        if len(hints_by_key) <= 1:
            return []

        ordered_hints = sorted(hints_by_key.values(), key=str.casefold)
        return [f"Conflicting title hints: {', '.join(ordered_hints)}."]

    def _to_contribution(self, row: sqlite3.Row) -> LineageContribution:
        source = str(row["evidence_source"] or row["artifact_source"] or "unknown")
        evidence_type = str(row["evidence_type"] or "raw_artifact")
        strength = str(row["strength"] or "unknown")
        evidence_value = self._json_object(row["evidence_value"])
        title_hint = evidence_value.get("title_hint")
        reasoning = (
            f"Title hint: {title_hint}."
            if title_hint
            else f"{source} contributed {strength} {evidence_type} evidence."
        )

        return LineageContribution(
            source=source,
            evidence_type=evidence_type,
            strength=strength,
            observed_at=row["observed_at"],
            evidence_id=row["evidence_id"],
            raw_ref=row["raw_ref"],
            title_hint=title_hint,
            reasoning=reasoning,
        )

    def _json_object(self, payload: object) -> dict[str, object]:
        if payload in (None, ""):
            return {}
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
        return {}

    def _stem(self, value: object) -> str | None:
        if not value:
            return None
        stem = PureWindowsPath(str(value)).stem
        return stem or None

    def _display_key(self, value: str | None) -> str:
        if not value:
            return ""
        return " ".join(str(value).casefold().split())
