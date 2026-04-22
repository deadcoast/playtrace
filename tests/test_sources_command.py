from __future__ import annotations

from io import StringIO
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.render.source_views import render_sources
from playtrace.render.theme import get_theme
from playtrace.services.sources import SourcesRequest, SourcesService
from playtrace.services.sources import SourceEntry, SourcesSnapshot
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


def test_sources_view_surfaces_conflicts_between_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    scan_run_id = db.create_scan_run(["security_log", "userassist"])
    target = r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"

    artifacts = [
        RawArtifact(
            artifact_id="artifact:security",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4688:200",
            payload={"exe_path": target},
        ),
        RawArtifact(
            artifact_id="artifact:userassist",
            scan_run_id=scan_run_id,
            source=SourceName.USERASSIST,
            observed_at=datetime(2026, 4, 18, 18, 0, 10, tzinfo=timezone.utc),
            raw_ref="userassist:battlenet",
            payload={"exe_path": target},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:security",
            artifact_id="artifact:security",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": target, "title_hint": "Battle.net Launcher"},
        ),
        EvidenceRecord(
            evidence_id="evidence:userassist",
            artifact_id="artifact:userassist",
            source=SourceName.USERASSIST,
            evidence_type=EvidenceType.INTERACTIVE_LAUNCH,
            observed_at=datetime(2026, 4, 18, 18, 0, 10, tzinfo=timezone.utc),
            strength=EvidenceStrength.INTERACTIVE,
            value={"exe_path": target, "title_hint": "Battle.net"},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])

    snapshot = SourcesService().load(
        SourcesRequest(
            db_path=db_path,
            target=target,
            theme="mono",
        )
    )

    assert snapshot.conflicts


def test_sources_render_handles_conflict_panel(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    scan_run_id = db.create_scan_run(["security_log", "userassist"])
    target = r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"

    artifacts = [
        RawArtifact(
            artifact_id="artifact:security",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            raw_ref="security_log:4688:200",
            payload={"exe_path": target},
        ),
        RawArtifact(
            artifact_id="artifact:userassist",
            scan_run_id=scan_run_id,
            source=SourceName.USERASSIST,
            observed_at=datetime(2026, 4, 18, 18, 0, 10, tzinfo=timezone.utc),
            raw_ref="userassist:battlenet",
            payload={"exe_path": target},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:security",
            artifact_id="artifact:security",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc),
            strength=EvidenceStrength.EXACT,
            value={"exe_path": target, "title_hint": "Battle.net Launcher"},
        ),
        EvidenceRecord(
            evidence_id="evidence:userassist",
            artifact_id="artifact:userassist",
            source=SourceName.USERASSIST,
            evidence_type=EvidenceType.INTERACTIVE_LAUNCH,
            observed_at=datetime(2026, 4, 18, 18, 0, 10, tzinfo=timezone.utc),
            strength=EvidenceStrength.INTERACTIVE,
            value={"exe_path": target, "title_hint": "Battle.net"},
        ),
    ]
    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    db.finish_scan_run(scan_run_id, [])

    SourcesService().render(
        SourcesRequest(
            db_path=db_path,
            target=target,
            theme="mono",
        )
    )

    output = capsys.readouterr().out

    assert "Conflicts" in output


def test_render_sources_uses_ascii_safe_wrapping_and_missing_value_labels() -> None:
    snapshot = SourcesSnapshot(
        target="battle.net launcher",
        entries=[
            SourceEntry(
                source="userassist",
                evidence_type="foreground_usage",
                strength="interactive",
                observed_at=None,
                raw_ref=r"userassist:C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe",
                reasoning=(
                    "userassist contributed interactive foreground_usage evidence from "
                    "a long reference that should wrap instead of truncating."
                ),
            )
        ],
        conflicts=[],
    )
    buffer = StringIO()
    console = Console(file=buffer, width=56, color_system=None, force_terminal=False)

    render_sources(console, get_theme("mono"), snapshot)

    output = buffer.getvalue()

    assert "unknown" in output
    assert "—" not in output
    assert "…" not in output
