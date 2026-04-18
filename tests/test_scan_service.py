from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.models.repair import RepairCounts, RepairPreview
from playtrace.services.scanner import ScanRequest, ScannerService


def test_scan_service_returns_source_statuses_and_final_summary(tmp_path: Path) -> None:
    request = ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False)

    snapshot = ScannerService(
        collectors=[_SuccessfulCollector(), _FailingCollector()],
        parsers=[_SuccessfulParser(), _PassthroughParser()],
    ).run_for_snapshot(request)

    statuses = {status.source: status for status in snapshot.sources}

    assert snapshot.summary.total_sources == 2
    assert snapshot.summary.completed_sources == 1
    assert snapshot.summary.total_artifacts == 1
    assert snapshot.summary.total_evidence == 1
    assert snapshot.summary.warning_count == 1
    assert statuses["security_log"].status == "ready"
    assert statuses["prefetch"].status == "collect_failed"


def test_scan_command_never_finishes_without_rendering_summary(tmp_path: Path, capsys) -> None:
    request = ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False)

    ScannerService().render(request)

    output = capsys.readouterr().out

    assert "playtrace SCAN" in output
    assert "Summary" in output
    assert "Source Status" in output


def test_scan_service_preview_rebuild_does_not_apply_without_yes(tmp_path: Path) -> None:
    rebuild_service = _StubRebuildService()

    ScannerService(
        collectors=[_SuccessfulCollector()],
        parsers=[_SuccessfulParser()],
        rebuild_service=rebuild_service,
    ).render(
        ScanRequest(
            db_path=tmp_path / "playtrace.db",
            config_path=None,
            raw=None,
            rebuild=True,
            yes=False,
        )
    )

    assert rebuild_service.plan_calls == 1
    assert rebuild_service.apply_calls == 0


@dataclass(slots=True)
class _SuccessfulCollector:
    name: str = "security_log"

    def is_available(self) -> bool:
        return True

    def collect(self, context) -> list[RawArtifact]:
        return [
            RawArtifact(
                artifact_id="artifact:1",
                scan_run_id=context.scan_run_id,
                source=SourceName.SECURITY_LOG,
                observed_at=None,
                raw_ref="security_log:1",
                payload={"exe_path": r"C:\Games\Balatro\balatro.exe"},
            )
        ]


@dataclass(slots=True)
class _FailingCollector:
    name: str = "prefetch"

    def is_available(self) -> bool:
        return True

    def collect(self, context) -> list[RawArtifact]:
        raise RuntimeError("collector exploded")


@dataclass(slots=True)
class _SuccessfulParser:
    name: str = "security_log"

    def parse(self, artifacts) -> list[EvidenceRecord]:
        assert len(artifacts) == 1
        return [
            EvidenceRecord(
                evidence_id="evidence:1",
                artifact_id=artifacts[0].artifact_id,
                source=SourceName.SECURITY_LOG,
                evidence_type=EvidenceType.PROCESS_START,
                observed_at=None,
                strength=EvidenceStrength.EXACT,
                value={"exe_path": r"C:\Games\Balatro\balatro.exe"},
            )
        ]


@dataclass(slots=True)
class _PassthroughParser:
    name: str = "prefetch"

    def parse(self, artifacts) -> list[EvidenceRecord]:
        return []


class _StubRebuildService:
    def __init__(self) -> None:
        self.plan_calls = 0
        self.apply_calls = 0

    def plan(self, db_path: Path, settings=None):
        self.plan_calls += 1
        return RepairPreview(counts=RepairCounts())

    def apply(self, db_path: Path, *, preview, confirmed: bool):
        self.apply_calls += 1
        return preview
