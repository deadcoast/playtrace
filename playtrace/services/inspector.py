from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from playtrace.normalize.identity import IdentityNormalizer
from playtrace.render.console import build_console
from playtrace.render.source_views import render_inspection
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class InspectRequest:
    db_path: Path
    theme: str
    density: str
    target: str


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

            exe_ids = sorted({str(row["exe_id"]) for row in session_rows if row["exe_id"]})
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

        source_counter: Counter[str] = Counter()
        for row in session_rows:
            source_counter.update(json.loads(row["evidence_sources"]))

        evidence_sources = sorted(source_counter)
        evidence_ids = sorted(
            {
                evidence_id
                for row in session_rows
                for evidence_id in json.loads(row["evidence_ids"])
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
        theme = get_theme(request.theme)
        render_inspection(console, theme, detail)

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
