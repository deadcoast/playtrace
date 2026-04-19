from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.evidence import RawArtifact
from playtrace.models.doctor import DoctorFinding, DoctorSnapshot
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.models.repair import RepairCounts, RepairPreview
from playtrace.parsers.bam import BamParser
from playtrace.parsers.srum import SrumParser
from playtrace.services.doctor import DoctorRequest, DoctorService


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


def test_doctor_render_includes_remediation_guidance(tmp_path: Path, capsys) -> None:
    class StubAuditService:
        def load(self, request: object) -> DoctorSnapshot:
            return DoctorSnapshot(
                environment_findings=[
                    DoctorFinding(
                        severity="warn",
                        code="not-admin",
                        summary="Administrator access is disabled.",
                        remediation=["Relaunch the shell as Administrator and run `playtrace scan` again."],
                    )
                ],
                data_findings=[],
            )

    DoctorService(audit_service=StubAuditService()).render(
        DoctorRequest(db_path=tmp_path / "playtrace.db", theme="mono")
    )

    output = capsys.readouterr().out
    assert "How to correct this" in output
    assert "Administrator" in output


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


def test_doctor_service_preview_repair_does_not_apply_without_yes(tmp_path: Path) -> None:
    class StubRebuildService:
        def __init__(self) -> None:
            self.plan_calls = 0
            self.apply_calls = 0

        def plan(self, db_path: Path, settings=None):
            self.plan_calls += 1
            return RepairPreview(counts=RepairCounts())

        def apply(self, db_path: Path, *, preview, confirmed: bool):
            self.apply_calls += 1
            return preview

    rebuild_service = StubRebuildService()

    DoctorService(
        audit_service=StubAuditService(),
        rebuild_service=rebuild_service,
    ).render(
        DoctorRequest(
            db_path=tmp_path / "playtrace.db",
            theme="mono",
            repair=True,
            yes=False,
        )
    )

    assert rebuild_service.plan_calls == 1
    assert rebuild_service.apply_calls == 0


def test_doctor_service_preview_repair_applies_with_yes(tmp_path: Path) -> None:
    class StubRebuildService:
        def __init__(self) -> None:
            self.plan_calls = 0
            self.apply_calls = 0

        def plan(self, db_path: Path, settings=None):
            self.plan_calls += 1
            return RepairPreview(counts=RepairCounts())

        def apply(self, db_path: Path, *, preview, confirmed: bool, settings=None):
            assert confirmed is True
            self.apply_calls += 1
            return preview

    rebuild_service = StubRebuildService()

    DoctorService(
        audit_service=StubAuditService(),
        rebuild_service=rebuild_service,
    ).render(
        DoctorRequest(
            db_path=tmp_path / "playtrace.db",
            theme="mono",
            repair=True,
            yes=True,
        )
    )

    assert rebuild_service.plan_calls == 1
    assert rebuild_service.apply_calls == 1


class StubAuditService:
    def load(self, request: object) -> DoctorSnapshot:
        return DoctorSnapshot(environment_findings=[], data_findings=[])
