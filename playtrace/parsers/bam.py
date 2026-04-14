from __future__ import annotations

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class BamParser:
    name = SourceName.BAM.value

    def parse(self, artifacts: list[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            records.append(
                EvidenceRecord(
                    evidence_id=f"evidence:{self.name}:recent:{index}:{artifact.artifact_id}",
                    artifact_id=artifact.artifact_id,
                    source=SourceName.BAM,
                    evidence_type=EvidenceType.RECENT_EXECUTION,
                    observed_at=artifact.observed_at,
                    strength=EvidenceStrength.WEAK,
                    value=dict(artifact.payload),
                )
            )
        return records
