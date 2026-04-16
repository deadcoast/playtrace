from __future__ import annotations

from pathlib import Path

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
