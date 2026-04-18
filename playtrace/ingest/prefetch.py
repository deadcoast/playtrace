from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext


class PrefetchCollector:
    name = SourceName.PREFETCH.value
    _prefetch_dir = Path(r"C:\Windows\Prefetch")

    def is_available(self) -> bool:
        return self._prefetch_dir.exists() and self._prefetch_dir.is_dir()

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        prefetch_files = sorted(
            self._prefetch_dir.glob("*.pf"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        limit = 512 if context.full_scan else 128
        for index, prefetch_file in enumerate(prefetch_files[:limit], start=1):
            exe_name = prefetch_file.stem.split("-", 1)[0]
            if not exe_name:
                continue
            observed_at = datetime.fromtimestamp(prefetch_file.stat().st_mtime, tz=timezone.utc)
            payload = {
                "exe_name": exe_name,
                "last_run_times": [observed_at.isoformat()],
            }
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.PREFETCH,
                    observed_at=observed_at,
                    raw_ref=f"prefetch:{prefetch_file.name}",
                    payload=payload,
                )
            )
        return artifacts
