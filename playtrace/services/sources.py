from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from playtrace.render.console import build_console
from playtrace.render.source_views import render_sources
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class SourcesRequest:
    db_path: Path
    target: str
    theme: str


@dataclass(slots=True)
class SourceEntry:
    source: str
    evidence_type: str
    strength: str
    observed_at: str | None
    raw_ref: str


@dataclass(slots=True)
class SourcesSnapshot:
    target: str
    entries: list[SourceEntry] = field(default_factory=list)


class SourcesService:
    def load(self, request: SourcesRequest) -> SourcesSnapshot:
        db = Database(request.db_path)
        db.bootstrap()
        target = request.target.lower()
        entries: list[SourceEntry] = []

        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    artifacts.source AS artifact_source,
                    artifacts.payload AS artifact_payload,
                    artifacts.raw_ref AS raw_ref,
                    evidence_links.source AS evidence_source,
                    evidence_links.evidence_type AS evidence_type,
                    evidence_links.strength AS strength,
                    evidence_links.observed_at AS observed_at,
                    evidence_links.value AS evidence_value
                FROM artifacts
                LEFT JOIN evidence_links
                    ON evidence_links.artifact_id = artifacts.artifact_id
                ORDER BY COALESCE(evidence_links.observed_at, artifacts.observed_at) DESC
                """
            ).fetchall()

        for row in rows:
            payload = json.loads(row["artifact_payload"])
            evidence_value = json.loads(row["evidence_value"]) if row["evidence_value"] else {}
            haystacks = [
                json.dumps(payload).lower(),
                json.dumps(evidence_value).lower(),
                str(row["raw_ref"]).lower(),
            ]
            if not any(target in haystack for haystack in haystacks):
                continue

            entries.append(
                SourceEntry(
                    source=row["evidence_source"] or row["artifact_source"],
                    evidence_type=row["evidence_type"] or "raw_artifact",
                    strength=row["strength"] or "unknown",
                    observed_at=row["observed_at"],
                    raw_ref=row["raw_ref"],
                )
            )

        return SourcesSnapshot(target=request.target, entries=entries)

    def render(self, request: SourcesRequest) -> None:
        snapshot = self.load(request)
        console = build_console()
        theme = get_theme(request.theme)
        render_sources(console, theme, snapshot)
