from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RepairCounts:
    merged_titles: int = 0
    changed_titles: int = 0
    changed_sessions: int = 0
    remaining_duplicate_groups: int = 0


@dataclass(slots=True)
class RepairPreview:
    counts: RepairCounts
    title_changes: list[str] = field(default_factory=list)
    session_changes: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
