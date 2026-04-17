from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.report import CoverageSummary
from playtrace.models.title import TitleAggregate


@dataclass(slots=True)
class IdentityDashboardSnapshot:
    generated_at: datetime
    host_name: str
    scan_age: str
    coverage: CoverageSummary = field(default_factory=CoverageSummary)
    top_titles: list[TitleAggregate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
