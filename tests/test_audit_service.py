from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.title import TitleAggregate
from playtrace.services.audit import AuditRequest, AuditService
from playtrace.store.db import Database


def test_audit_engine_reports_blocked_sources_and_duplicate_titles(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles(
        [
            TitleAggregate(
                title_id="title:elden-ring",
                title="Elden Ring",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher=None,
                first_seen=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
            ),
            TitleAggregate(
                title_id="title:elden-ring-alt",
                title="elden ring",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher=None,
                first_seen=datetime(2026, 4, 12, 18, 42, 3, tzinfo=timezone.utc),
            ),
        ]
    )

    snapshot = AuditService(
        platform_name="Windows",
        os_name="nt",
        admin_checker=lambda: False,
        path_status=lambda path: "present" if path.endswith("Prefetch") else "inaccessible",
    ).load(AuditRequest(db_path=db.path))

    environment_codes = {finding.code for finding in snapshot.environment_findings}
    data_codes = {finding.code for finding in snapshot.data_findings}

    assert "not-admin" in environment_codes
    assert "duplicate-titles" in data_codes
    duplicate_finding = next(finding for finding in snapshot.data_findings if finding.code == "duplicate-titles")
    assert any("doctor --repair" in step for step in duplicate_finding.remediation)
