from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.title import TitleAggregate
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class CoverageSummary:
    tracked_titles: int = 0
    confirmed_runtime_seconds: int = 0
    estimated_runtime_seconds: int = 0
    confirmed_sessions: int = 0
    unmapped_executables: int = 0


@dataclass(slots=True)
class ReportSnapshot:
    generated_at: datetime
    host_name: str
    coverage: CoverageSummary
    stale_data: bool = False
    top_titles: list[TitleAggregate] = field(default_factory=list)
    recent_sessions: list[SessionRecord] = field(default_factory=list)
    recent_session_titles: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
