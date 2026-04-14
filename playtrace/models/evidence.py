from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


@dataclass(slots=True)
class RawArtifact:
    artifact_id: str
    scan_run_id: str
    source: SourceName
    observed_at: datetime | None
    raw_ref: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    artifact_id: str
    source: SourceName
    evidence_type: EvidenceType
    observed_at: datetime | None
    strength: EvidenceStrength
    value: dict[str, Any] = field(default_factory=dict)
