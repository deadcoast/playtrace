from __future__ import annotations

from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.store.db import Database


def test_bootstrap_creates_v2_tables(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"scan_runs", "artifacts", "evidence_links", "title_executables"} <= names


def test_titles_can_be_rebuilt_from_artifacts_and_mappings(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log"])
    artifacts = [
        RawArtifact(
            artifact_id="artifact:start",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=None,
            raw_ref="security_log:4688:15320",
            payload={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
        RawArtifact(
            artifact_id="artifact:end",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=None,
            raw_ref="security_log:4689:15320",
            payload={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:start",
            artifact_id="artifact:start",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=None,
            strength=EvidenceStrength.EXACT,
            value={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
        EvidenceRecord(
            evidence_id="evidence:end",
            artifact_id="artifact:end",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_EXIT,
            observed_at=None,
            strength=EvidenceStrength.EXACT,
            value={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
    ]

    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO mappings (
                mapping_id, target, title, classification, launcher,
                ignore, created_at, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mapping:1",
                "path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe",
                "Elden Ring",
                "game",
                "Steam",
                0,
                "2026-04-11T18:00:00+00:00",
                "high",
            ),
        )
        conn.commit()

    db.rebuild_from_artifacts_and_mappings()

    with db.connect() as conn:
        title_row = conn.execute("SELECT title, launcher FROM titles").fetchone()
        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        executable_count = conn.execute("SELECT COUNT(*) FROM executables").fetchone()[0]

    assert title_row["title"] == "Elden Ring"
    assert title_row["launcher"] == "Steam"
    assert session_count == 1
    assert executable_count == 1
