from __future__ import annotations

from pathlib import Path

from playtrace.services.reporter import ReportRequest, ReporterService
from playtrace.store.db import Database


def test_report_does_not_seed_demo_data(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    ReporterService().render_default(
        ReportRequest(
            db_path=db_path,
            config_path=None,
            theme="mono",
            density="comfortable",
            limit=5,
        )
    )

    with db.connect() as conn:
        title_count = conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0]

    assert title_count == 0
