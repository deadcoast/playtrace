from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.ingest.windows_support import query_security_events
from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext


class SecurityLogCollector:
    name = SourceName.SECURITY_LOG.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        max_events = 2048 if context.full_scan else 256
        for index, payload in enumerate(query_security_events(max_events=max_events), start=1):
            artifacts.append(
                RawArtifact(
                    artifact_id=f"artifact:{self.name}:{index}:{uuid4().hex}",
                    scan_run_id=context.scan_run_id,
                    source=SourceName.SECURITY_LOG,
                    observed_at=datetime.fromisoformat(payload["timestamp"]),
                    raw_ref=(
                        f"security_log:{payload['event_id']}:"
                        f"{payload['pid'] if payload['pid'] is not None else 'unknown'}"
                    ),
                    payload=payload,
                )
            )
        return artifacts
