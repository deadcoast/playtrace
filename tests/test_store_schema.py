from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import (
    Classification,
    ConfidenceLevel,
    EvidenceStrength,
    EvidenceType,
    RuntimeConfidence,
    SourceName,
)
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, TitleAggregate
from playtrace.store.db import Database
from playtrace.utils.clock import Clock


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

    with db.connect() as conn:
        session_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
        }

    assert "evidence_ids" in session_columns


def test_scan_runs_store_timezone_aware_timestamps(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log"])
    db.finish_scan_run(scan_run_id, [])

    with db.connect() as conn:
        row = conn.execute(
            "SELECT started_at, finished_at FROM scan_runs WHERE scan_run_id = ?",
            (scan_run_id,),
        ).fetchone()

    assert row["started_at"].endswith("+00:00")
    assert row["finished_at"].endswith("+00:00")


def test_scan_runs_use_shared_clock_utility(tmp_path: Path, monkeypatch) -> None:
    fixed = datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(Clock, "utc_now", staticmethod(lambda: fixed))

    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log"])
    db.finish_scan_run(scan_run_id, [])

    with db.connect() as conn:
        row = conn.execute(
            "SELECT started_at, finished_at FROM scan_runs WHERE scan_run_id = ?",
            (scan_run_id,),
        ).fetchone()

    assert row["started_at"] == fixed.isoformat()
    assert row["finished_at"] == fixed.isoformat()


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


def test_replace_sessions_persists_evidence_ids(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    db.replace_sessions(
        [
            SessionRecord(
                session_id="session:1",
                title_id="title:elden_ring",
                exe_id="path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe",
                user_sid="S-1-5-21-demo",
                started_at=None,
                ended_at=None,
                duration_seconds=None,
                confidence=RuntimeConfidence.EXACT,
                evidence_sources=["security_log"],
                evidence_ids=["evidence:start", "evidence:end"],
                parent_chain=["steam.exe"],
            )
        ]
    )

    with db.connect() as conn:
        row = conn.execute("SELECT evidence_ids FROM sessions WHERE session_id = ?", ("session:1",)).fetchone()

    assert row["evidence_ids"] == '["evidence:start", "evidence:end"]'


def test_load_user_mappings_ignores_invalid_classification(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO mappings (
                mapping_id, target, title, classification, launcher,
                ignore, created_at, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mapping:invalid",
                r"D:\Games\Balatro\balatro.exe",
                "Balatro",
                "definitely-not-valid",
                None,
                0,
                "2026-04-11T18:00:00+00:00",
                "high",
            ),
        )
        conn.commit()

    mappings = db.load_user_mappings()

    assert len(mappings) == 1
    assert mappings[0].classification is None
    assert mappings[0].normalized_key == "path:d:\\games\\balatro\\balatro.exe"


def test_count_duplicate_title_groups_uses_normalized_title_keys(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles(
        [
            _title("title:elden-ring", "ELDEN RING"),
            _title("title:eldenring", "eldenring"),
        ]
    )

    assert db.count_duplicate_title_groups() == 1


def test_load_snapshot_counts_confirmed_sessions_from_sessions_table(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles([_title("title:balatro", "Balatro", launches_confirmed=7)])
    db.replace_sessions(
        [
            SessionRecord(
                session_id="session:1",
                title_id="title:balatro",
                exe_id="exe:balatro",
                user_sid="S-1-5-21-demo",
                started_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 4, 11, 18, 30, 0, tzinfo=timezone.utc),
                duration_seconds=1800,
                confidence=RuntimeConfidence.EXACT,
                evidence_sources=["security_log"],
            )
        ]
    )

    snapshot = db.load_snapshot(limit=5)

    assert snapshot.coverage.confirmed_sessions == 1


def test_load_sessions_orders_by_actual_timestamp_when_offsets_differ(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles(
        [
            _title("title:offset-later", "Offset Later"),
            _title("title:utc-earlier", "UTC Earlier"),
        ]
    )

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, title_id, exe_id, user_sid, started_at, ended_at,
                duration_seconds, foreground_seconds, bytes_in, bytes_out,
                confidence, evidence_sources, evidence_ids, parent_chain, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session:offset-later",
                "title:offset-later",
                "exe:1",
                None,
                "2026-04-12T00:30:00-07:00",
                "2026-04-12T01:30:00-07:00",
                3600,
                0,
                0,
                0,
                "exact",
                "[]",
                "[]",
                "[]",
                "[]",
            ),
        )
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, title_id, exe_id, user_sid, started_at, ended_at,
                duration_seconds, foreground_seconds, bytes_in, bytes_out,
                confidence, evidence_sources, evidence_ids, parent_chain, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session:utc-earlier",
                "title:utc-earlier",
                "exe:2",
                None,
                "2026-04-12T07:00:00+00:00",
                "2026-04-12T08:00:00+00:00",
                3600,
                0,
                0,
                0,
                "exact",
                "[]",
                "[]",
                "[]",
                "[]",
            ),
        )
        conn.commit()

    sessions = db.load_sessions(title=None, days=3650, limit=10)

    assert [title for title, _ in sessions[:2]] == ["Offset Later", "UTC Earlier"]


def _title(
    title_id: str,
    title: str,
    *,
    launches_confirmed: int = 0,
) -> TitleAggregate:
    return TitleAggregate(
        title_id=title_id,
        title=title,
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        launches=LaunchStats(
            confirmed=launches_confirmed,
            inferred=0,
            gui=0,
            confidence=ConfidenceLevel.HIGH,
        ),
    )
