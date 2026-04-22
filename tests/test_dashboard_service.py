from __future__ import annotations

from io import StringIO
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from playtrace.models.dashboard import IdentityDashboardSnapshot
from playtrace.models.report import CoverageSummary
from playtrace.render.dashboard_views import render_dashboard
from playtrace.render.theme import get_theme
from playtrace.services.dashboard import DashboardRequest, DashboardService


def test_dashboard_service_loads_latest_persisted_identity_snapshot(tmp_path: Path) -> None:
    snapshot = DashboardService().load(
        DashboardRequest(db_path=tmp_path / "playtrace.db", refresh=False, theme="mono")
    )

    assert snapshot.top_titles is not None


def test_dashboard_refresh_runs_scan_before_render(tmp_path: Path) -> None:
    class FakeScannerService:
        def __init__(self) -> None:
            self.called = False

        def run(self, request: object) -> None:
            self.called = True

    service = DashboardService(scanner=FakeScannerService())
    service.render(DashboardRequest(db_path=tmp_path / "playtrace.db", refresh=True, theme="mono"))

    assert service.scanner.called


def test_dashboard_render_uses_identity_block_sections(tmp_path: Path, capsys) -> None:
    DashboardService().render(DashboardRequest(db_path=tmp_path / "playtrace.db", refresh=False, theme="mono"))

    output = capsys.readouterr().out

    assert "playtrace ME" in output
    assert "Coverage" in output


def test_dashboard_render_uses_unknown_runtime_and_ascii_notes() -> None:
    snapshot = IdentityDashboardSnapshot(
        generated_at=datetime(2026, 4, 22, 10, 0, 1, tzinfo=timezone.utc),
        host_name="homeone",
        scan_age="6h ago",
        coverage=CoverageSummary(
            tracked_titles=1,
            confirmed_runtime_seconds=0,
            estimated_runtime_seconds=0,
            confirmed_sessions=0,
            unmapped_executables=1,
        ),
        warnings=["Administrator access is disabled."],
    )
    buffer = StringIO()
    console = Console(file=buffer, width=52, color_system=None, force_terminal=False)

    render_dashboard(console, get_theme("mono"), snapshot)

    output = buffer.getvalue()

    assert "UNKNOWN" in output
    assert "0h 00m" not in output
    assert "•" not in output
