from __future__ import annotations

from dataclasses import dataclass

from playtrace.models.artifacts import ArtifactRecord
from playtrace.parsers.base import ArtifactParser, ParseContext


@dataclass(slots=True)
class IngestResult:
    artifacts: list[ArtifactRecord]
    warnings: list[str]


class IngestOrchestrator:
    def __init__(self, parsers: list[ArtifactParser]) -> None:
        self.parsers = parsers

    def run(self, context: ParseContext, selected_sources: set[str] | None = None) -> IngestResult:
        artifacts: list[ArtifactRecord] = []
        warnings: list[str] = []

        for parser in self.parsers:
            if selected_sources and parser.name not in selected_sources:
                continue
            if not parser.is_available():
                warnings.append(f"Source unavailable: {parser.name}")
                continue
            try:
                artifacts.extend(parser.parse(context))
            except Exception as exc:
                warnings.append(f"Failed to parse {parser.name}: {exc}")

        return IngestResult(artifacts=artifacts, warnings=warnings)