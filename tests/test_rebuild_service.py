from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.models.title import TitleAggregate
from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.services.rebuild import RebuildService
from playtrace.store.db import Database


def test_rebuild_service_previews_changes_without_mutating_database(tmp_path: Path) -> None:
    db = _seed_duplicate_database(tmp_path)

    preview = RebuildService().plan(db.path)

    assert preview.title_changes
    assert Database(db.path).count_duplicate_title_groups() == 1


def test_rebuild_service_apply_requires_explicit_confirmation(tmp_path: Path) -> None:
    db = _seed_duplicate_database(tmp_path)

    with pytest.raises(PermissionError):
        RebuildService().apply(
            db.path,
            preview=RebuildService().plan(db.path),
            confirmed=False,
        )


def _seed_duplicate_database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    scan_run_id = db.create_scan_run(["security_log"])

    exe_path = r"D:\Games\ELDEN RING\eldenring.exe"
    artifacts = [
        RawArtifact(
            artifact_id="artifact:start",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4688:100",
            payload={"exe_path": exe_path, "pid": 100, "user_sid": "S-1-5-21-demo"},
        ),
        RawArtifact(
            artifact_id="artifact:end",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 19, 0, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4689:100",
            payload={"exe_path": exe_path, "pid": 100, "user_sid": "S-1-5-21-demo"},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:start",
            artifact_id="artifact:start",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": exe_path, "pid": 100, "user_sid": "S-1-5-21-demo"},
        ),
        EvidenceRecord(
            evidence_id="evidence:end",
            artifact_id="artifact:end",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_EXIT,
            observed_at=datetime(2026, 4, 18, 19, 0, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": exe_path, "pid": 100, "user_sid": "S-1-5-21-demo"},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])
    db.replace_titles(
        [
            TitleAggregate(
                title_id="title:elden_ring",
                title="ELDEN RING",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher="Steam",
            ),
            TitleAggregate(
                title_id="title:eldenring",
                title="eldenring",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.LOW,
                launcher="Steam",
            ),
        ]
    )
    return db
