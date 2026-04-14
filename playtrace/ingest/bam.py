from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_BAM_ENTRIES = [
    {
        "exe_path": r"D:\Games\Balatro\balatro.exe",
        "last_run": "2026-04-11T18:00:00+00:00",
    }
]


class BamCollector:
    name = SourceName.BAM.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_BAM_ENTRIES, start=1):
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.BAM,
                    observed_at=datetime.fromisoformat(payload["last_run"]),
                    raw_ref=f"bam:{payload['exe_path']}",
                    payload=payload,
                )
            )
        return artifacts
