from __future__ import annotations

import json
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
    evidence_ids: list[str] = field(default_factory=list)
    parent_chains: list[list[str]] = field(default_factory=list)


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

        evidence_sources = sorted(
            {
                source
                for row in session_rows
                for source in json.loads(row["evidence_sources"])
            }
        )
        evidence_ids = sorted(
            {
                evidence_id
                for row in session_rows
                for evidence_id in json.loads(row["evidence_ids"])
            }
        )
        parent_chains = [json.loads(row["parent_chain"]) for row in session_rows]

        return InspectionDetail(
            title=title_row["title"],
            runtime_confidence=title_row["runtime_confidence"],
            evidence_sources=evidence_sources,
            evidence_ids=evidence_ids,
            parent_chains=parent_chains,
        )

    def render(self, request: InspectRequest) -> None:
        detail = self.load(request)
        console = build_console()
        theme = get_theme(request.theme)
        render_inspection(console, theme, detail)
