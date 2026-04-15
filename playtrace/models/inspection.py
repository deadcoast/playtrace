from __future__ import annotations

from dataclasses import dataclass, field


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
