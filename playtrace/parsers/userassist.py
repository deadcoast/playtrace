from __future__ import annotations

from datetime import datetime
from typing import Sequence

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class UserAssistParser:
    name = SourceName.USERASSIST.value

    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            if artifact.payload.get("run_count") is not None:
                records.append(
                    EvidenceRecord(
                        evidence_id=f"evidence:{self.name}:launch:{index}:{artifact.artifact_id}",
                        artifact_id=artifact.artifact_id,
                        source=SourceName.USERASSIST,
                        evidence_type=EvidenceType.INTERACTIVE_LAUNCH,
                        observed_at=self._last_run(artifact),
                        strength=EvidenceStrength.INTERACTIVE,
                        value=dict(artifact.payload),
                    )
                )

            if artifact.payload.get("focus_time_ms") is not None:
                records.append(
                    EvidenceRecord(
                        evidence_id=f"evidence:{self.name}:focus:{index}:{artifact.artifact_id}",
                        artifact_id=artifact.artifact_id,
                        source=SourceName.USERASSIST,
                        evidence_type=EvidenceType.FOREGROUND_USAGE,
                        observed_at=self._last_run(artifact),
                        strength=EvidenceStrength.INTERACTIVE,
                        value=dict(artifact.payload),
                    )
                )

        return records

    def _last_run(self, artifact: RawArtifact) -> datetime | None:
        value = artifact.payload.get("last_run")
        if not value:
            return artifact.observed_at
        return datetime.fromisoformat(str(value))
