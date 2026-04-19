from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawSourcesInput, UNSET
from playtrace.render.console import build_console
from playtrace.render.source_views import render_sources
from playtrace.render.theme import get_theme
from playtrace.services.lineage import LineageService


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
    reasoning: str = ""


@dataclass(slots=True)
class SourcesSnapshot:
    target: str
    entries: list[SourceEntry] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


class SourcesService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
        lineage_service: LineageService | None = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()
        self.lineage_service = lineage_service or LineageService()

    def load(self, request: SourcesRequest) -> SourcesSnapshot:
        lineage_snapshot = self.lineage_service.load_sources(request.db_path, request.target)
        return SourcesSnapshot(
            target=request.target,
            entries=[
                SourceEntry(
                    source=contribution.source,
                    evidence_type=contribution.evidence_type,
                    strength=contribution.strength,
                    observed_at=contribution.observed_at,
                    raw_ref=contribution.raw_ref or "",
                    reasoning=contribution.reasoning,
                )
                for contribution in lineage_snapshot.contributions
            ],
            conflicts=lineage_snapshot.conflicts,
        )

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
