from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class ExecutableIdentity:
    exe_id: str
    normalized_key: str
    path: str | None
    filename: str | None
    original_filename: str | None
    product_name: str | None
    file_description: str | None
    signer: str | None
    company_name: str | None
    sha1: str | None
    classification: Classification = Classification.UNKNOWN
    classification_confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    ignored: bool = False
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    aliases: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)