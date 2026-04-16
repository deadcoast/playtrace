from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.doctor import DoctorFinding, DoctorSnapshot
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.parsers.bam import BamParser
from playtrace.parsers.srum import SrumParser
from playtrace.services.doctor import DoctorRequest, DoctorService
from playtrace.store.db import Database


def test_srum_parser_emits_activity_windows() -> None:
    artifact = RawArtifact(
        artifact_id="artifact:srum:1",
        scan_run_id="scan:test",
        source=SourceName.SRUM,
        observed_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        raw_ref="srum:application-resource-usage",
        payload={
            "window_start": "2026-04-11T18:00:00+00:00",
            "window_end": "2026-04-11T19:00:00+00:00",
            "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
            "user_sid": "S-1-5-21-demo",
            "bytes_sent": 412340,
            "bytes_received": 12034440,
        },
    )

    records = SrumParser().parse([artifact])

    assert len(records) == 1
    assert records[0].evidence_type == EvidenceType.ACTIVITY_WINDOW


def test_bam_parser_emits_weak_execution_evidence() -> None:
    artifact = RawArtifact(
        artifact_id="artifact:bam:1",
        scan_run_id="scan:test",
        source=SourceName.BAM,
        observed_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        raw_ref="bam:D:\\Games\\Balatro\\balatro.exe",
        payload={
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "last_run": "2026-04-11T18:00:00+00:00",
        },
    )

    records = BamParser().parse([artifact])

    assert len(records) == 1
    assert records[0].evidence_type == EvidenceType.RECENT_EXECUTION
    assert records[0].strength == EvidenceStrength.WEAK


def test_doctor_reports_exact_runtime_coverage_expectations(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log", "prefetch"])
    artifacts = [
        RawArtifact(
            artifact_id="artifact:start",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
            raw_ref="security_log:4688:15320",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
        RawArtifact(
            artifact_id="artifact:end",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
            raw_ref="security_log:4689:15320",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
        RawArtifact(
            artifact_id="artifact:prefetch",
            scan_run_id=scan_run_id,
            source=SourceName.PREFETCH,
            observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
            raw_ref="prefetch:ELDENRING.EXE-1A2B3C4D.pf",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:start",
            artifact_id="artifact:start",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={},
        ),
        EvidenceRecord(
            evidence_id="evidence:end",
            artifact_id="artifact:end",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_EXIT,
            observed_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={},
        ),
        EvidenceRecord(
            evidence_id="evidence:prefetch",
            artifact_id="artifact:prefetch",
            source=SourceName.PREFETCH,
            evidence_type=EvidenceType.EXECUTION_COUNT,
            observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
            strength=EvidenceStrength.STRONG,
            value={},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])

    snapshot = DoctorService().load(DoctorRequest(db_path=db_path, theme="mono"))

    assert snapshot.exact_runtime_support == "available"
    assert "prefetch" in snapshot.supporting_sources
    assert any("exact runtime" in line.lower() for line in snapshot.guidance)


def test_doctor_snapshot_can_hold_environment_and_data_findings() -> None:
    snapshot = DoctorSnapshot(
        environment_findings=[],
        data_findings=[
            DoctorFinding(
                severity="warn",
                code="missing-sessions",
                summary="No sessions available",
            )
        ],
    )

    assert snapshot.environment_findings == []
    assert snapshot.data_findings == [
        DoctorFinding(
            severity="warn",
            code="missing-sessions",
            summary="No sessions available",
        )
    ]
