from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.services.sources import SourcesRequest, SourcesService
from playtrace.store.db import Database


def test_sources_view_lists_source_specific_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log", "prefetch"])
    artifacts = [
        RawArtifact(
            artifact_id="artifact:security",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
            raw_ref="security_log:4688:15320",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
        RawArtifact(
            artifact_id="artifact:prefetch",
            scan_run_id=scan_run_id,
            source=SourceName.PREFETCH,
            observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
            raw_ref="prefetch:ELDENRING.EXE-1A2B3C4D.pf",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:security",
            artifact_id="artifact:security",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
        EvidenceRecord(
            evidence_id="evidence:prefetch",
            artifact_id="artifact:prefetch",
            source=SourceName.PREFETCH,
            evidence_type=EvidenceType.EXECUTION_COUNT,
            observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
            strength=EvidenceStrength.STRONG,
            value={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])

    snapshot = SourcesService().load(
        SourcesRequest(
            db_path=db_path,
            target="eldenring.exe",
            theme="mono",
        )
    )

    assert {entry.source for entry in snapshot.entries} == {"security_log", "prefetch"}
    assert {entry.evidence_type for entry in snapshot.entries} == {"process_start", "execution_count"}


def test_sources_view_matches_normalized_executable_paths(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    scan_run_id = db.create_scan_run(["userassist"])
    artifacts = [
        RawArtifact(
            artifact_id="artifact:userassist",
            scan_run_id=scan_run_id,
            source=SourceName.USERASSIST,
            observed_at=datetime(2026, 4, 16, 8, 40, 52, tzinfo=timezone.utc),
            raw_ref=r"userassist:{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}\Battle.net\Battle.net Launcher.exe",
            payload={
                "entry": r"{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}\Battle.net\Battle.net Launcher.exe",
                "exe_path": r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe",
            },
        )
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:userassist",
            artifact_id="artifact:userassist",
            source=SourceName.USERASSIST,
            evidence_type=EvidenceType.INTERACTIVE_LAUNCH,
            observed_at=datetime(2026, 4, 16, 8, 40, 52, tzinfo=timezone.utc),
            strength=EvidenceStrength.INTERACTIVE,
            value={"exe_path": r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"},
        )
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])

    snapshot = SourcesService().load(
        SourcesRequest(
            db_path=db_path,
            target=r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe",
            theme="mono",
        )
    )

    assert len(snapshot.entries) == 1
    assert snapshot.entries[0].source == "userassist"
    assert snapshot.entries[0].evidence_type == "interactive_launch"
