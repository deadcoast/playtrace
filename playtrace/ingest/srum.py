from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_SRUM_ENTRIES = [
    {
        "window_start": "2026-04-11T18:00:00+00:00",
        "window_end": "2026-04-11T19:00:00+00:00",
        "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
        "user_sid": "S-1-5-21-demo",
        "bytes_sent": 412340,
        "bytes_received": 12034440,
    }
]


class SrumCollector:
    name = SourceName.SRUM.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_SRUM_ENTRIES, start=1):
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.SRUM,
                    observed_at=datetime.fromisoformat(payload["window_start"]),
                    raw_ref="srum:application-resource-usage",
                    payload=payload,
                )
            )
        return artifacts
