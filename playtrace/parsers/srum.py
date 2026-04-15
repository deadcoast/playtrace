from __future__ import annotations

from typing import Sequence

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class SrumParser:
    name = SourceName.SRUM.value

    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            records.append(
                EvidenceRecord(
                    evidence_id=f"evidence:{self.name}:window:{index}:{artifact.artifact_id}",
                    artifact_id=artifact.artifact_id,
                    source=SourceName.SRUM,
                    evidence_type=EvidenceType.ACTIVITY_WINDOW,
                    observed_at=artifact.observed_at,
                    strength=EvidenceStrength.STRONG,
                    value=dict(artifact.payload),
                )
            )
        return records
