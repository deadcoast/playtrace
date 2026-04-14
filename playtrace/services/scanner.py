from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

from playtrace.ingest.orchestrator import IngestOrchestrator
from playtrace.ingest.registry import build_collectors, build_parsers
from playtrace.parsers.base import CollectContext
from playtrace.store.db import Database


@dataclass(slots=True)
class ScanRequest:
    db_path: Path
    config_path: Path | None
    sources: list[str]
    full: bool = False


class ScannerService:
    def run(self, request: ScanRequest) -> None:
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
