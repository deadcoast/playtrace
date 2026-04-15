from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_PREFETCH_ENTRIES = [
    {
        "exe_name": "ELDENRING.EXE",
        "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
        "run_count": 34,
        "last_run_times": [
            "2026-04-11T18:42:05+00:00",
            "2026-04-10T20:11:07+00:00",
        ],
    }
]


class PrefetchCollector:
    name = SourceName.PREFETCH.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_PREFETCH_ENTRIES, start=1):
            observed_at = None
            last_run_times = payload.get("last_run_times")
            if isinstance(last_run_times, list) and last_run_times:
                observed_at = datetime.fromisoformat(str(last_run_times[0]))
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.PREFETCH,
                    observed_at=observed_at,
                    raw_ref=f"prefetch:{payload['exe_name']}",
                    payload=payload,
                )
            )
        return artifacts
