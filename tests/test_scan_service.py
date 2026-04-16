from __future__ import annotations

from pathlib import Path

from playtrace.services.scanner import ScanRequest, ScannerService


def test_scan_service_returns_source_statuses_and_final_summary(tmp_path: Path) -> None:
    request = ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False)

    snapshot = ScannerService().run_for_snapshot(request)

    assert snapshot.sources
    assert snapshot.summary.total_artifacts >= 0


def test_scan_command_never_finishes_without_rendering_summary(tmp_path: Path, capsys) -> None:
    request = ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False)

    ScannerService().render(request)

    output = capsys.readouterr().out

    assert "playtrace SCAN" in output
    assert "Summary" in output
    assert "Source Status" in output
