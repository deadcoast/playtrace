from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class UserMapping:
    mapping_id: str
    target: str
    title: str
    classification: Classification | None
    launcher: str | None
    ignore: bool
    created_at: datetime
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH