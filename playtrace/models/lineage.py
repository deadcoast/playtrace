from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LineageContribution:
    source: str
    evidence_type: str
    strength: str
    observed_at: str | None = None
    raw_ref: str | None = None
    reasoning: str = ""


@dataclass(slots=True)
class EntityLineageSnapshot:
    title: str
    runtime_confidence: str
    confidence_reasons: list[str] = field(default_factory=list)
    alternate_titles: list[str] = field(default_factory=list)
    contributions: list[LineageContribution] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourcesLineageSnapshot:
    target: str
    contributions: list[LineageContribution] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
