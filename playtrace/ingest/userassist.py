from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_USERASSIST_ENTRIES = [
    {
        "entry": r"C:\Program Files (x86)\Steam\steam.exe",
        "run_count": 19,
        "focus_time_ms": 24034000,
        "last_run": "2026-04-11T18:41:50+00:00",
        "user_sid": "S-1-5-21-demo",
    }
]


class UserAssistCollector:
    name = SourceName.USERASSIST.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_USERASSIST_ENTRIES, start=1):
            observed_at = None
            last_run = payload.get("last_run")
            if last_run:
                observed_at = datetime.fromisoformat(str(last_run))
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.USERASSIST,
                    observed_at=observed_at,
                    raw_ref=f"userassist:{payload['entry']}",
                    payload=payload,
                )
            )
        return artifacts
