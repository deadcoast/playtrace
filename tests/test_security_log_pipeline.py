from __future__ import annotations

from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.services.scanner import ScanRequest, ScannerService
from playtrace.store.db import Database


def test_scan_pipeline_stores_raw_artifacts_before_sessions(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    service = ScannerService(
        collectors=[_SecurityCollector()],
        parsers=[_SecurityParser()],
    )

    request = ScanRequest(
        db_path=db_path,
        config_path=None,
        sources=["security_log"],
        full=True,
    )
    service.run(request)

    with db.connect() as conn:
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        scan_run_count = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]

    assert artifact_count >= 1
    assert scan_run_count == 1


class _SecurityCollector:
    name = "security_log"

    def is_available(self) -> bool:
        return True

    def collect(self, context) -> list[RawArtifact]:
        return [
            RawArtifact(
                artifact_id="artifact:security:1",
                scan_run_id=context.scan_run_id,
                source=SourceName.SECURITY_LOG,
                observed_at=None,
                raw_ref="security_log:4688:15320",
                payload={"exe_path": r"C:\Games\Balatro\balatro.exe"},
            )
        ]


class _SecurityParser:
    name = "security_log"

    def parse(self, artifacts) -> list[EvidenceRecord]:
        return [
            EvidenceRecord(
                evidence_id="evidence:security:1",
                artifact_id=artifacts[0].artifact_id,
                source=SourceName.SECURITY_LOG,
                evidence_type=EvidenceType.PROCESS_START,
                observed_at=None,
                strength=EvidenceStrength.EXACT,
                value=dict(artifacts[0].payload),
            )
        ]
