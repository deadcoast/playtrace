from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawMeInput, RawScanInput, UNSET
from playtrace.models.dashboard import IdentityDashboardSnapshot
from playtrace.render.console import build_console
from playtrace.render.dashboard_views import render_dashboard
from playtrace.render.theme import get_theme
from playtrace.services.audit import AuditRequest, AuditService
from playtrace.services.scanner import ScanRequest, ScannerService
from playtrace.store.db import Database


@dataclass(slots=True, init=False)
class DashboardRequest:
    db_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawMeInput

    def __init__(
        self,
        *,
        db_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawMeInput | None = None,
        refresh: bool | None = None,
        theme: str | None = None,
        density: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawMeInput(
            refresh=refresh if refresh is not None else UNSET,
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
        )


class DashboardService:
    def __init__(
        self,
        *,
        scanner: ScannerService | object | None = None,
        audit_service: AuditService | object | None = None,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
    ) -> None:
        self.scanner = scanner or ScannerService()
        self.audit_service = audit_service or AuditService()
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()

    def load(self, request: DashboardRequest) -> IdentityDashboardSnapshot:
        resolved = self._resolve(request)
        if resolved.refresh:
            self.scanner.run(
                ScanRequest(
                    db_path=request.db_path,
                    config_path=request.config_path,
                    spec_name=request.spec_name,
                    raw=RawScanInput(),
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
        resolved = self._resolve(request)
        snapshot = self.load(request)
        console = build_console()
        theme = get_theme(resolved.presentation.theme)
        render_dashboard(console, theme, snapshot)
        return snapshot

    def _resolve(self, request: DashboardRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_me(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )

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
