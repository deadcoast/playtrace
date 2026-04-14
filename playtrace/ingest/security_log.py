from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_SECURITY_EVENTS = [
    {
        "event_id": 4688,
        "timestamp": "2026-04-11T18:42:03+00:00",
        "pid": 15320,
        "parent_pid": 9012,
        "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
        "command_line": r"\"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe\"",
        "user_sid": "S-1-5-21-demo",
    }
]


class SecurityLogCollector:
    name = SourceName.SECURITY_LOG.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_SECURITY_EVENTS, start=1):
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.SECURITY_LOG,
                    observed_at=datetime.fromisoformat(payload["timestamp"]),
                    raw_ref=f"security_log:{payload['event_id']}:{payload['pid']}",
                    payload=payload,
                )
            )
        return artifacts
