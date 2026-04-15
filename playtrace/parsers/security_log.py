from __future__ import annotations

from typing import Sequence

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class SecurityLogParser:
    name = SourceName.SECURITY_LOG.value

    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            event_id = artifact.payload.get("event_id")
            evidence_type = None
            if event_id == 4688:
                evidence_type = EvidenceType.PROCESS_START
            elif event_id == 4689:
                evidence_type = EvidenceType.PROCESS_EXIT

            if evidence_type is None:
                continue

            records.append(
                EvidenceRecord(
                    evidence_id=f"evidence:{self.name}:{index}:{artifact.artifact_id}",
                    artifact_id=artifact.artifact_id,
                    source=SourceName.SECURITY_LOG,
                    evidence_type=evidence_type,
                    observed_at=artifact.observed_at,
                    strength=EvidenceStrength.EXACT,
                    value=dict(artifact.payload),
                )
            )
        return records
