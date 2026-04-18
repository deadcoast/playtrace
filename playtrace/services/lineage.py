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
        with db.connect() as conn:
            return self._load_entity(db=db, conn=conn, target=target)

    def load_entities(self, db_path: Path, targets: list[str]) -> list[EntityLineageSnapshot]:
        db = Database(db_path)
        db.bootstrap()
        with db.connect() as conn:
            return [self._load_entity(db=db, conn=conn, target=target) for target in targets]

    def load_sources(self, db_path: Path, target: str) -> SourcesLineageSnapshot:
        db = Database(db_path)
        db.bootstrap()
        with db.connect() as conn:
            _, executable_rows, evidence_rows = self._resolve_lineage_rows(
                db=db,
                conn=conn,
                target=target,
            )

        return SourcesLineageSnapshot(
            target=target,
            contributions=[self._to_contribution(row) for row in evidence_rows],
            conflicts=self._collect_conflicts(evidence_rows),
        )

    def _load_entity(
        self,
        *,
        db: Database,
        conn: sqlite3.Connection,
        target: str,
    ) -> EntityLineageSnapshot:
        title_row, executable_rows, evidence_rows = self._resolve_lineage_rows(
            db=db,
            conn=conn,
            target=target,
        )
        if title_row is None:
            return EntityLineageSnapshot(
                title=target,
                runtime_confidence="unknown",
                confidence_reasons=["No persisted title matched this target yet."],
                contributions=[self._to_contribution(row) for row in evidence_rows],
                conflicts=self._collect_conflicts(evidence_rows),
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

    def _resolve_lineage_rows(
        self,
        *,
        db: Database,
        conn: sqlite3.Connection,
        target: str,
    ) -> tuple[sqlite3.Row | None, list[sqlite3.Row], list[sqlite3.Row]]:
        normalized_target = self.normalizer.normalize_executable_target(target)
        title_row = db.find_lineage_title(target, normalized_target, conn=conn)
        executable_rows = db.load_lineage_executables(
            title_id=str(title_row["title_id"]) if title_row is not None else None,
            normalized_target=normalized_target,
            conn=conn,
        )
        evidence_rows = db.load_lineage_evidence_rows(
            search_terms=self._search_terms(
                target=target,
                normalized_target=normalized_target,
                title=str(title_row["title"]) if title_row is not None else None,
                executable_rows=executable_rows,
            ),
            conn=conn,
        )
        return title_row, executable_rows, evidence_rows

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
