from __future__ import annotations

from typing import Sequence

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class AmCacheParser:
    name = SourceName.AMCACHE.value

    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            records.append(
                EvidenceRecord(
                    evidence_id=f"evidence:{self.name}:identity:{index}:{artifact.artifact_id}",
                    artifact_id=artifact.artifact_id,
                    source=SourceName.AMCACHE,
                    evidence_type=EvidenceType.IDENTITY,
                    observed_at=artifact.observed_at,
                    strength=EvidenceStrength.STRONG,
                    value=dict(artifact.payload),
                )
            )
        return records
