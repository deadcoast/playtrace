from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import RuntimeConfidence


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    title_id: str | None
    exe_id: str
    user_sid: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    foreground_seconds: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    confidence: RuntimeConfidence = RuntimeConfidence.UNKNOWN
    evidence_sources: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    parent_chain: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
