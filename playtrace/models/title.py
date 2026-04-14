from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class RuntimeStats:
    confirmed_seconds: int = 0
    estimated_seconds: int = 0
    foreground_seconds: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN


@dataclass(slots=True)
class LaunchStats:
    confirmed: int = 0
    inferred: int = 0
    gui: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN


@dataclass(slots=True)
class TitleAggregate:
    title_id: str
    title: str
    classification: Classification
    classification_confidence: ConfidenceLevel
    title_confidence: ConfidenceLevel
    launcher: str | None
    primary_exe_id: str | None = None
    runtime: RuntimeStats = field(default_factory=RuntimeStats)
    launches: LaunchStats = field(default_factory=LaunchStats)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    executable_ids: list[str] = field(default_factory=list)
    suppressed_executable_ids: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
