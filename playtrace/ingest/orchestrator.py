from __future__ import annotations

from dataclasses import dataclass

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.parsers.base import CollectContext, EvidenceParser, RawCollector


@dataclass(slots=True)
class IngestResult:
    artifacts: list[RawArtifact]
    evidence: list[EvidenceRecord]
    warnings: list[str]


class IngestOrchestrator:
    def __init__(self, collectors: list[RawCollector], parsers: list[EvidenceParser]) -> None:
        self.collectors = collectors
        self.parsers = parsers

    def run(self, context: CollectContext, selected_sources: set[str] | None = None) -> IngestResult:
        artifacts: list[RawArtifact] = []
        evidence: list[EvidenceRecord] = []
        warnings: list[str] = []
        artifacts_by_source: dict[str, list[RawArtifact]] = {}

        for collector in self.collectors:
            if selected_sources and collector.name not in selected_sources:
                continue
            if not collector.is_available():
                warnings.append(f"Source unavailable: {collector.name}")
                continue
            try:
                collected = collector.collect(context)
            except Exception as exc:
                warnings.append(f"Failed to collect {collector.name}: {exc}")
                continue

            artifacts.extend(collected)
            artifacts_by_source[collector.name] = collected

        for parser in self.parsers:
            if selected_sources and parser.name not in selected_sources:
                continue
            try:
                parsed = parser.parse(artifacts_by_source.get(parser.name, []))
            except Exception as exc:
                warnings.append(f"Failed to parse {parser.name}: {exc}")
                continue
            evidence.extend(parsed)

        return IngestResult(artifacts=artifacts, evidence=evidence, warnings=warnings)
