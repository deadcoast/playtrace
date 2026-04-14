from __future__ import annotations

from datetime import datetime

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class PrefetchParser:
    name = SourceName.PREFETCH.value

    def parse(self, artifacts: list[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            run_count = artifact.payload.get("run_count")
            if run_count is not None:
                records.append(
                    EvidenceRecord(
                        evidence_id=f"evidence:{self.name}:count:{index}:{artifact.artifact_id}",
                        artifact_id=artifact.artifact_id,
                        source=SourceName.PREFETCH,
                        evidence_type=EvidenceType.EXECUTION_COUNT,
                        observed_at=artifact.observed_at,
                        strength=EvidenceStrength.STRONG,
                        value=dict(artifact.payload),
                    )
                )

            for recent_index, value in enumerate(artifact.payload.get("last_run_times", []), start=1):
                records.append(
                    EvidenceRecord(
                        evidence_id=f"evidence:{self.name}:recent:{recent_index}:{artifact.artifact_id}",
                        artifact_id=artifact.artifact_id,
                        source=SourceName.PREFETCH,
                        evidence_type=EvidenceType.RECENT_EXECUTION,
                        observed_at=datetime.fromisoformat(value),
                        strength=EvidenceStrength.STRONG,
                        value={**artifact.payload, "last_run": value},
                    )
                )

        return records
