from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

from playtrace.ingest.orchestrator import IngestOrchestrator
from playtrace.ingest.registry import build_collectors, build_parsers
from playtrace.parsers.base import CollectContext
from playtrace.store.db import Database

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from playtrace.parsers.security_log import SecurityLogParser
from playtrace.render.console import build_console
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class ScanRequest:
    db_path: Path
    config_path: Path | None
    sources: list[str]
    days: int
    theme: str
    full: bool = False

class ScannerService:
    def run(self, request: ScanRequest) -> None:
<<<<<<< HEAD
        console = build_console()
        theme = get_theme(request.theme)
        db = Database(request.db_path)
        db.bootstrap()

        parser = SecurityLogParser()
        if not parser.is_available():
            raise SystemExit(
                "Security log parser is unavailable. Run on Windows with permission to read the Security log."
            )

        sessions = parser.parse_sessions(request.days)
        db.replace_sessions_from_scan(sessions, source="security_log")
        db.rebuild_titles_from_sessions()

        header = Text()
        header.append("playtrace SCAN\n", style=f"bold {theme.accent}")
        header.append("Historical session ingestion from Windows Security log", style=theme.dim)
        console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))

        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", ratio=2)
        table.add_column("Value", ratio=3)
        table.add_row("Source", "Security Log (4688/4689)")
        table.add_row("Days requested", str(request.days))
        table.add_row("Sessions inserted", str(len(sessions)))
        table.add_row("Titles rebuilt", str(db.count_titles()))
        table.add_row("Database", str(request.db_path.resolve()))
        console.print(table)
=======
        db = Database(request.db_path)
        db.bootstrap()

        selected_sources = request.sources or [collector.name for collector in build_collectors()]
        scan_run_id = db.create_scan_run(selected_sources)
        context = CollectContext(
            scan_run_id=scan_run_id,
            host_name=socket.gethostname(),
            temp_dir=Path(gettempdir()),
            full_scan=request.full,
        )

        orchestrator = IngestOrchestrator(
            collectors=build_collectors(),
            parsers=build_parsers(),
        )
        result = orchestrator.run(context, selected_sources=set(selected_sources))

        db.replace_artifacts_for_scan(scan_run_id, result.artifacts)
        db.replace_evidence_for_scan(scan_run_id, result.evidence)
        db.rebuild_from_artifacts_and_mappings()
        db.finish_scan_run(scan_run_id, result.warnings)
>>>>>>> 5826d2c01e206f624bf2fa0731bedd097ed65711
