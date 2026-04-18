from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawInspectInput, UNSET
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.render.console import build_console
from playtrace.render.source_views import render_inspection
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True, init=False)
class InspectRequest:
    db_path: Path
    target: str
    config_path: Path | None
    spec_name: str | None
    raw: RawInspectInput

    def __init__(
        self,
        *,
        db_path: Path,
        target: str,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawInspectInput | None = None,
        theme: str | None = None,
        density: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.target = target
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawInspectInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
        )


@dataclass(slots=True)
class InspectionDetail:
    title: str
    runtime_confidence: str
    evidence_sources: list[str] = field(default_factory=list)
    evidence_source_counts: dict[str, int] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    parent_chains: list[list[str]] = field(default_factory=list)
    mapping_source: str = "heuristic"
    confidence_reasoning: list[str] = field(default_factory=list)


class InspectorService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()

    def load(self, request: InspectRequest) -> InspectionDetail:
        db = Database(request.db_path)
        db.bootstrap()
        normalized_target = IdentityNormalizer().normalize_executable_target(request.target)

        with db.connect() as conn:
            title_row = conn.execute(
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
                    request.target,
                    request.target,
                    normalized_target or request.target,
                    normalized_target or request.target,
                ),
            ).fetchone()

            if title_row is None:
                return InspectionDetail(
                    title=request.target,
                    runtime_confidence="unknown",
                )

            session_rows = conn.execute(
                """
                SELECT *
                FROM sessions
                WHERE title_id = ?
                   OR exe_id = ?
                ORDER BY started_at ASC
                """,
                (title_row["title_id"], normalized_target or request.target),
            ).fetchall()

            title_executable_rows = conn.execute(
                """
                SELECT exe_id
                FROM title_executables
                WHERE title_id = ?
                ORDER BY exe_id ASC
                """,
                (title_row["title_id"],),
            ).fetchall()
            exe_ids = sorted(
                {
                    str(row["exe_id"])
                    for row in session_rows
                    if row["exe_id"]
                }
                | {
                    str(row["exe_id"])
                    for row in title_executable_rows
                    if row["exe_id"]
                }
            )
            mapping_rows = []
            if exe_ids:
                placeholders = ", ".join("?" for _ in exe_ids)
                mapping_rows = conn.execute(
                    f"""
                    SELECT target, title, classification, launcher, ignore, confidence
                    FROM mappings
                    WHERE target IN ({placeholders})
                    """,
                    tuple(exe_ids),
                ).fetchall()

            fallback_evidence_rows = []
            if exe_ids and not session_rows:
                fallback_evidence_rows = conn.execute(
                    """
                    SELECT
                        artifacts.source AS artifact_source,
                        artifacts.payload AS artifact_payload,
                        artifacts.raw_ref AS raw_ref,
                        evidence_links.evidence_id AS evidence_id,
                        evidence_links.source AS evidence_source,
                        evidence_links.value AS evidence_value
                    FROM artifacts
                    LEFT JOIN evidence_links
                      ON evidence_links.artifact_id = artifacts.artifact_id
                    ORDER BY COALESCE(evidence_links.observed_at, artifacts.observed_at) DESC
                    """
                ).fetchall()

        source_counter: Counter[str] = Counter()
        for row in session_rows:
            source_counter.update(json.loads(row["evidence_sources"]))

        evidence_ids = {
            evidence_id
            for row in session_rows
            for evidence_id in json.loads(row["evidence_ids"])
        }
        if not source_counter and fallback_evidence_rows:
            for row in fallback_evidence_rows:
                if not self._matches_executable_evidence(row, exe_ids):
                    continue
                source = row["evidence_source"] or row["artifact_source"]
                if source:
                    source_counter.update([str(source)])
                if row["evidence_id"]:
                    evidence_ids.add(str(row["evidence_id"]))

        evidence_sources = sorted(source_counter)
        evidence_ids = sorted(
            {
                evidence_id
                for evidence_id in evidence_ids
            }
        )
        parent_chains = [json.loads(row["parent_chain"]) for row in session_rows]
        mapping_source = "manual" if mapping_rows else "heuristic"
        confidence_reasoning = self._confidence_reasoning(
            runtime_confidence=title_row["runtime_confidence"],
            evidence_sources=evidence_sources,
            mapping_source=mapping_source,
        )

        return InspectionDetail(
            title=title_row["title"],
            runtime_confidence=title_row["runtime_confidence"],
            evidence_sources=evidence_sources,
            evidence_source_counts=dict(source_counter),
            evidence_ids=evidence_ids,
            parent_chains=parent_chains,
            mapping_source=mapping_source,
            confidence_reasoning=confidence_reasoning,
        )

    def render(self, request: InspectRequest) -> None:
        detail = self.load(request)
        console = build_console()
        resolved = self._resolve(request)
        theme = get_theme(resolved.presentation.theme)
        render_inspection(console, theme, detail)

    def _resolve(self, request: InspectRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_inspect(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )

    def _confidence_reasoning(
        self,
        *,
        runtime_confidence: str,
        evidence_sources: list[str],
        mapping_source: str,
    ) -> list[str]:
        reasoning: list[str] = []

        if runtime_confidence == "exact":
            reasoning.append("Exact runtime is available because matched process start and exit evidence exists.")
        elif runtime_confidence == "estimated":
            reasoning.append("Runtime is estimated from supporting evidence instead of exact start and exit pairs.")
        else:
            reasoning.append("Runtime confidence is unknown because exact or estimated session evidence is missing.")

        if evidence_sources:
            reasoning.append(f"Evidence currently comes from: {', '.join(evidence_sources)}.")
        else:
            reasoning.append("No evidence sources are linked to this title yet.")

        if mapping_source == "manual":
            reasoning.append("Title resolution includes a manual mapping override.")
        else:
            reasoning.append("Title resolution is currently heuristic-derived.")

        return reasoning

    def _matches_executable_evidence(self, row, exe_ids: list[str]) -> bool:
        haystacks = [
            str(row["raw_ref"]).lower(),
            str(row["artifact_payload"]).lower(),
            str(row["evidence_value"] or "").lower(),
        ]
        haystacks.extend(haystack.replace("\\\\", "\\") for haystack in list(haystacks))
        for exe_id in exe_ids:
            term = self._search_term_for_executable(exe_id)
            if term and any(term in haystack for haystack in haystacks):
                return True
        return False

    def _search_term_for_executable(self, exe_id: str) -> str | None:
        lowered = exe_id.lower()
        if lowered.startswith("path:"):
            return lowered[5:]
        if lowered.startswith("sha1:"):
            return lowered[5:]
        return None
