from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from playtrace.models.enums import EvidenceStrength, SourceName


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    source: SourceName
    observed_at: datetime | None
    user_sid: str | None
    exe_path: str | None
    exe_name: str | None
    process_id: int | None = None
    parent_process_id: int | None = None
    parent_exe_name: str | None = None
    launch_count: int | None = None
    run_timestamps: list[datetime] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    foreground_seconds: int | None = None
    bytes_in: int | None = None
    bytes_out: int | None = None
    product_name: str | None = None
    file_description: str | None = None
    company_name: str | None = None
    signer: str | None = None
    original_filename: str | None = None
    sha1: str | None = None
    strength: EvidenceStrength = EvidenceStrength.UNKNOWN
    raw: dict[str, Any] = field(default_factory=dict)