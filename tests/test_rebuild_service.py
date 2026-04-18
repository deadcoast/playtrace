from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from playtrace.config.runtime import ReconstructionSettings
from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.models.title import TitleAggregate
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


def test_rebuild_service_counts_merged_titles_even_when_new_titles_are_added(tmp_path: Path) -> None:
    db = _seed_duplicate_database_with_new_title(tmp_path)

    preview = RebuildService().plan(db.path)

    assert preview.counts.merged_titles == 1


def test_rebuild_service_counts_in_place_session_updates() -> None:
    service = RebuildService()
    current = [
        _session_record(
            session_id="session:1",
            started_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 4, 18, 18, 5, 0, tzinfo=timezone.utc),
        )
    ]
    proposed = [
        _session_record(
            session_id="session:1",
            started_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 4, 18, 18, 8, 0, tzinfo=timezone.utc),
        )
    ]

    changes = service._session_changes(current, proposed)

    assert changes == ["update session session:1"]


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


def _seed_duplicate_database_with_new_title(tmp_path: Path) -> Database:
    db = _seed_duplicate_database(tmp_path)
    scan_run_id = db.create_scan_run(["security_log"])
    exe_path = r"D:\Games\Balatro\balatro.exe"
    artifacts = [
        RawArtifact(
            artifact_id="artifact:balatro:start",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 20, 0, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4688:200",
            payload={"exe_path": exe_path, "pid": 200, "user_sid": "S-1-5-21-demo"},
        ),
        RawArtifact(
            artifact_id="artifact:balatro:end",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 20, 30, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4689:200",
            payload={"exe_path": exe_path, "pid": 200, "user_sid": "S-1-5-21-demo"},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:balatro:start",
            artifact_id="artifact:balatro:start",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 18, 20, 0, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": exe_path, "pid": 200, "user_sid": "S-1-5-21-demo"},
        ),
        EvidenceRecord(
            evidence_id="evidence:balatro:end",
            artifact_id="artifact:balatro:end",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_EXIT,
            observed_at=datetime(2026, 4, 18, 20, 30, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": exe_path, "pid": 200, "user_sid": "S-1-5-21-demo"},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])
    return db


def _session_record(
    *,
    session_id: str,
    started_at: datetime,
    ended_at: datetime,
) -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        title_id="title:balatro",
        exe_id="path:d:\\games\\balatro\\balatro.exe",
        user_sid="S-1-5-21-demo",
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=int((ended_at - started_at).total_seconds()),
        confidence=RuntimeConfidence.EXACT,
        evidence_sources=["security_log"],
        evidence_ids=[f"{session_id}:start", f"{session_id}:end"],
        parent_chain=["steam.exe"],
    )
