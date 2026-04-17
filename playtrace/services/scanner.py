from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Sequence

from playtrace.ingest.orchestrator import IngestOrchestrator, IngestSourceStatus
from playtrace.ingest.registry import build_collectors, build_parsers
from playtrace.parsers.base import CollectContext
from playtrace.render.console import build_console
from playtrace.render.scan_views import render_scan
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class ScanRequest:
    db_path: Path
    config_path: Path | None
    sources: list[str]
    full: bool = False
    theme: str = "midnight"
    density: str = "comfortable"


@dataclass(slots=True)
class ScanSummary:
    total_sources: int
    completed_sources: int
    total_artifacts: int
    total_evidence: int
    warning_count: int
    tracked_titles: int = 0
    confirmed_sessions: int = 0
    unmapped_executables: int = 0


@dataclass(slots=True)
class ScanLiveSnapshot:
    scan_run_id: str
    generated_at: datetime
    host_name: str
    selected_sources: list[str]
    sources: list[IngestSourceStatus]
    warnings: list[str]
    summary: ScanSummary


class ScannerService:
    def __init__(
        self,
        *,
        collectors: Sequence | None = None,
        parsers: Sequence | None = None,
    ) -> None:
        self.collectors = list(collectors) if collectors is not None else build_collectors()
        self.parsers = list(parsers) if parsers is not None else build_parsers()

    def run(self, request: ScanRequest) -> ScanLiveSnapshot:
        return self.run_for_snapshot(request)

    def run_for_snapshot(self, request: ScanRequest) -> ScanLiveSnapshot:
        db = Database(request.db_path)
        db.bootstrap()

        selected_sources = request.sources or [collector.name for collector in self.collectors]
        scan_run_id = db.create_scan_run(selected_sources)
        context = CollectContext(
            scan_run_id=scan_run_id,
            host_name=socket.gethostname(),
            temp_dir=Path(gettempdir()),
            full_scan=request.full,
        )

        orchestrator = IngestOrchestrator(
            collectors=self.collectors,
            parsers=self.parsers,
        )
        result = orchestrator.run(context, selected_sources=set(selected_sources))

        db.replace_artifacts_for_scan(scan_run_id, result.artifacts)
        db.replace_evidence_for_scan(scan_run_id, result.evidence)
        db.rebuild_from_artifacts_and_mappings()
        db.finish_scan_run(scan_run_id, result.warnings)

        report_snapshot = db.load_snapshot(limit=5)
        completed_sources = sum(
            1 for status in result.source_statuses if status.status in {"collected", "ready", "empty"}
        )

        return ScanLiveSnapshot(
            scan_run_id=scan_run_id,
            generated_at=datetime.now(timezone.utc),
            host_name=context.host_name,
            selected_sources=selected_sources,
            sources=result.source_statuses,
            warnings=result.warnings,
            summary=ScanSummary(
                total_sources=len(result.source_statuses),
                completed_sources=completed_sources,
                total_artifacts=len(result.artifacts),
                total_evidence=len(result.evidence),
                warning_count=len(result.warnings),
                tracked_titles=report_snapshot.coverage.tracked_titles,
                confirmed_sessions=report_snapshot.coverage.confirmed_sessions,
                unmapped_executables=report_snapshot.coverage.unmapped_executables,
            ),
        )

    def render(self, request: ScanRequest) -> ScanLiveSnapshot:
        snapshot = self.run_for_snapshot(request)
        console = build_console()
        theme = get_theme(request.theme)
        render_scan(console, theme, snapshot)
        return snapshot
