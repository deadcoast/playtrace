from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ScanRun:
    scan_run_id: str
    started_at: datetime
    host_name: str
    selected_sources: list[str] = field(default_factory=list)
    finished_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)
