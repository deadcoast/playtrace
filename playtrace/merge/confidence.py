from __future__ import annotations

from playtrace.models.enums import ConfidenceLevel
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord


def title_confidence_for_mapping(mapping: UserMapping | None) -> ConfidenceLevel:
    if mapping is not None:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM


def launches_confidence(sessions: list[SessionRecord]) -> ConfidenceLevel:
    if sessions:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.UNKNOWN
