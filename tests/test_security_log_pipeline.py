from __future__ import annotations

from pathlib import Path

from playtrace.services.scanner import ScanRequest, ScannerService
from playtrace.store.db import Database


def test_scan_pipeline_stores_raw_artifacts_before_sessions(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    service = ScannerService()

    request = ScanRequest(
        db_path=db_path,
        config_path=None,
        sources=["security_log"],
        full=True,
    )
    service.run(request)

    with db.connect() as conn:
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        scan_run_count = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]

    assert artifact_count >= 1
    assert scan_run_count == 1
