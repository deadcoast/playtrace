from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.dashboard import IdentityDashboardSnapshot
from playtrace.render.console import build_console
from playtrace.render.dashboard_views import render_dashboard
from playtrace.render.theme import get_theme
from playtrace.services.audit import AuditRequest, AuditService
from playtrace.services.scanner import ScanRequest, ScannerService
from playtrace.store.db import Database


@dataclass(slots=True)
class DashboardRequest:
    db_path: Path
    refresh: bool
    theme: str


class DashboardService:
    def __init__(
        self,
        *,
        scanner: ScannerService | object | None = None,
        audit_service: AuditService | object | None = None,
    ) -> None:
        self.scanner = scanner or ScannerService()
        self.audit_service = audit_service or AuditService()

    def load(self, request: DashboardRequest) -> IdentityDashboardSnapshot:
        if request.refresh:
            self.scanner.run(
                ScanRequest(
                    db_path=request.db_path,
                    config_path=None,
                    sources=[],
                    full=False,
                )
            )

        db = Database(request.db_path)
        db.bootstrap()
        report_snapshot = db.load_snapshot(limit=5)
        host_name, latest_scan_at = db.load_latest_scan_context()
        audit_snapshot = self.audit_service.load(AuditRequest(db_path=request.db_path))

        warnings = list(report_snapshot.warnings)
        warnings.extend(finding.summary for finding in audit_snapshot.environment_findings)
        warnings.extend(finding.summary for finding in audit_snapshot.data_findings)

        return IdentityDashboardSnapshot(
            generated_at=datetime.now(timezone.utc),
            host_name=host_name or report_snapshot.host_name,
            scan_age=self._format_scan_age(latest_scan_at),
            coverage=report_snapshot.coverage,
            top_titles=report_snapshot.top_titles,
            warnings=warnings,
        )

    def render(self, request: DashboardRequest) -> IdentityDashboardSnapshot:
        snapshot = self.load(request)
        console = build_console()
        theme = get_theme(request.theme)
        render_dashboard(console, theme, snapshot)
        return snapshot

    def _format_scan_age(self, latest_scan_at: datetime | None) -> str:
        if latest_scan_at is None:
            return "never scanned"

        delta = datetime.now(timezone.utc) - latest_scan_at
        if delta.days >= 1:
            return f"{delta.days}d ago"

        hours = delta.seconds // 3600
        if hours >= 1:
            return f"{hours}h ago"

        minutes = delta.seconds // 60
        if minutes >= 1:
            return f"{minutes}m ago"

        return "just now"
