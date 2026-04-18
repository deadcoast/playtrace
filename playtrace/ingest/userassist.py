from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from playtrace.ingest.windows_support import collect_userassist_payloads
from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import SourceName
from playtrace.parsers.base import CollectContext


class UserAssistCollector:
    name = SourceName.USERASSIST.value

    def is_available(self) -> bool:
        return True

    def collect(self, context: CollectContext) -> list[RawArtifact]:
        artifacts: list[RawArtifact] = []
        for index, payload in enumerate(collect_userassist_payloads(), start=1):
            observed_at = (
                datetime.fromisoformat(str(payload["last_run"]))
                if payload.get("last_run")
                else None
            )
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
