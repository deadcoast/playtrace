from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext

SAMPLE_AMCACHE_ENTRIES = [
    {
        "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
        "sha1": "abc123",
        "product_name": "ELDEN RING",
        "company_name": "FromSoftware, Inc.",
        "file_description": "ELDEN RING",
        "original_filename": "eldenring.exe",
    }
]


class AmCacheCollector:
    name = SourceName.AMCACHE.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(SAMPLE_AMCACHE_ENTRIES, start=1):
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.AMCACHE,
                    observed_at=datetime.now(),
                    raw_ref=f"amcache:{payload['exe_path']}",
                    payload=payload,
                )
            )
        return artifacts
