from __future__ import annotations

from dataclasses import dataclass, field

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.parsers.base import CollectContext, EvidenceParser, RawCollector


@dataclass(slots=True)
class IngestResult:
    artifacts: list[RawArtifact]
    evidence: list[EvidenceRecord]
    warnings: list[str]
    source_statuses: list["IngestSourceStatus"]


@dataclass(slots=True)
class IngestSourceStatus:
    source: str
    status: str
    artifacts: int = 0
    evidence: int = 0
    warnings: list[str] = field(default_factory=list)


class IngestOrchestrator:
    def __init__(self, collectors: list[RawCollector], parsers: list[EvidenceParser]) -> None:
        self.collectors = collectors
        self.parsers = parsers

    def run(self, context: CollectContext, selected_sources: set[str] | None = None) -> IngestResult:
        artifacts: list[RawArtifact] = []
        evidence: list[EvidenceRecord] = []
        warnings: list[str] = []
        artifacts_by_source: dict[str, list[RawArtifact]] = {}
        source_statuses: dict[str, IngestSourceStatus] = {}

        for collector in self.collectors:
            if selected_sources and collector.name not in selected_sources:
                continue
            status = source_statuses.setdefault(
                collector.name,
                IngestSourceStatus(source=collector.name, status="pending"),
            )
            if not collector.is_available():
                warning = f"Source unavailable: {collector.name}"
                warnings.append(warning)
                status.status = "unavailable"
                status.warnings.append(warning)
                continue
            try:
                collected = collector.collect(context)
            except Exception as exc:
                warning = f"Failed to collect {collector.name}: {exc}"
                warnings.append(warning)
                status.status = "collect_failed"
                status.warnings.append(warning)
                continue

            artifacts.extend(collected)
            artifacts_by_source[collector.name] = collected
            status.artifacts = len(collected)
            status.status = "collected" if collected else "empty"

        for parser in self.parsers:
            if selected_sources and parser.name not in selected_sources:
                continue
            status = source_statuses.setdefault(
                parser.name,
                IngestSourceStatus(source=parser.name, status="pending"),
            )
            if status.status in {"unavailable", "collect_failed"}:
                continue
            try:
                parsed = parser.parse(artifacts_by_source.get(parser.name, []))
            except Exception as exc:
                warning = f"Failed to parse {parser.name}: {exc}"
                warnings.append(warning)
                status.status = "parse_failed"
                status.warnings.append(warning)
                continue
            evidence.extend(parsed)
            status.evidence = len(parsed)
            status.status = "ready" if status.artifacts or status.evidence else "empty"

        return IngestResult(
            artifacts=artifacts,
            evidence=evidence,
            warnings=warnings,
            source_statuses=list(source_statuses.values()),
        )
