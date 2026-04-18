from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawSourcesInput, UNSET
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.render.console import build_console
from playtrace.render.source_views import render_sources
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True, init=False)
class SourcesRequest:
    db_path: Path
    target: str
    config_path: Path | None
    spec_name: str | None
    raw: RawSourcesInput

    def __init__(
        self,
        *,
        db_path: Path,
        target: str,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawSourcesInput | None = None,
        theme: str | None = None,
        density: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.target = target
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawSourcesInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
        )


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
    def __init__(
        self,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()

    def load(self, request: SourcesRequest) -> SourcesSnapshot:
        db = Database(request.db_path)
        db.bootstrap()
        target = request.target.lower()
        normalized_target = IdentityNormalizer().normalize_executable_target(request.target)
        search_terms = [target]
        if normalized_target and normalized_target.startswith("path:"):
            search_terms.append(normalized_target[5:])
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
            haystacks.extend(haystack.replace("\\\\", "\\") for haystack in list(haystacks))
            if not any(term in haystack for term in search_terms for haystack in haystacks):
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
        resolved = self._resolve(request)
        theme = get_theme(resolved.presentation.theme)
        render_sources(console, theme, snapshot)

    def _resolve(self, request: SourcesRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_sources(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )
