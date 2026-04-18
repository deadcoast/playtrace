from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.config.runtime import ReconstructionSettings
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
        session_row = conn.execute(
            "SELECT title_id, exe_id FROM sessions"
        ).fetchone()

    assert title_row["title"] == "Elden Ring"
    assert title_row["launcher"] == "Steam"
    assert session_count == 1
    assert executable_count == 1
    assert session_row["title_id"] == "title:elden_ring"
    assert session_row["exe_id"] == "path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe"


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


def test_purge_legacy_sample_scan_runs_removes_scaffold_data(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    scan_run_id = db.create_scan_run(
        ["security_log", "prefetch", "userassist", "amcache", "srum", "bam"]
    )
    artifacts = [
        RawArtifact(
            artifact_id="artifact:amcache",
            scan_run_id=scan_run_id,
            source=SourceName.AMCACHE,
            observed_at=None,
            raw_ref=r"amcache:D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
            payload={"exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"},
        ),
        RawArtifact(
            artifact_id="artifact:bam",
            scan_run_id=scan_run_id,
            source=SourceName.BAM,
            observed_at=None,
            raw_ref=r"bam:D:\Games\Balatro\balatro.exe",
            payload={"exe_path": r"D:\Games\Balatro\balatro.exe"},
        ),
        RawArtifact(
            artifact_id="artifact:prefetch",
            scan_run_id=scan_run_id,
            source=SourceName.PREFETCH,
            observed_at=None,
            raw_ref="prefetch:ELDENRING.EXE",
            payload={"exe_name": "ELDENRING.EXE"},
        ),
        RawArtifact(
            artifact_id="artifact:security",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=None,
            raw_ref="security_log:4688:15320",
            payload={"event_id": 4688},
        ),
        RawArtifact(
            artifact_id="artifact:srum",
            scan_run_id=scan_run_id,
            source=SourceName.SRUM,
            observed_at=None,
            raw_ref="srum:application-resource-usage",
            payload={"window_start": "2026-04-11T18:00:00+00:00"},
        ),
        RawArtifact(
            artifact_id="artifact:userassist",
            scan_run_id=scan_run_id,
            source=SourceName.USERASSIST,
            observed_at=None,
            raw_ref=r"userassist:C:\Program Files (x86)\Steam\steam.exe",
            payload={"entry": r"C:\Program Files (x86)\Steam\steam.exe"},
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id=f"evidence:{artifact.artifact_id}",
            artifact_id=artifact.artifact_id,
            source=artifact.source,
            evidence_type=EvidenceType.IDENTITY,
            observed_at=None,
            strength=EvidenceStrength.STRONG,
            value=dict(artifact.payload),
        )
        for artifact in artifacts
    ]

    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)

    removed = db.purge_legacy_sample_scan_runs()

    with db.connect() as conn:
        scan_runs = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        evidence_count = conn.execute("SELECT COUNT(*) FROM evidence_links").fetchone()[0]

    assert removed == 1
    assert scan_runs == 0
    assert artifact_count == 0
    assert evidence_count == 0


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


def test_load_titles_sort_by_launches_includes_gui_launches(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles(
        [
            _title(
                "title:gui-heavy",
                "GUI Heavy",
                launches_confirmed=0,
                launches_inferred=0,
                launches_gui=3,
            ),
            _title(
                "title:confirmed-light",
                "Confirmed Light",
                launches_confirmed=1,
                launches_inferred=0,
                launches_gui=0,
            ),
        ]
    )

    titles = db.load_titles(
        sort_by="launches",
        classification=None,
        launcher=None,
        limit=10,
    )

    assert [title.title for title in titles[:2]] == ["GUI Heavy", "Confirmed Light"]


def test_rebuild_uses_configured_session_merge_window(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    _seed_session_merge_edge_case(db)

    db.rebuild_from_artifacts_and_mappings()
    baseline_sessions = db.count_sessions()

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(session_merge_dedupe_window_minutes=10)
    )

    assert baseline_sessions == 2
    assert db.count_sessions() == 1


def test_rebuild_uses_configured_duplicate_auto_merge(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    _seed_duplicate_evidence(
        db,
        product_names=["ELDEN RING", "eldenring"],
    )

    db.rebuild_from_artifacts_and_mappings()
    baseline_duplicate_groups = db.count_duplicate_title_groups()

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(duplicate_auto_merge=True)
    )

    assert baseline_duplicate_groups == 1
    assert db.count_duplicate_title_groups() == 0


def test_rebuild_uses_configured_duplicate_similarity_threshold(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    _seed_duplicate_evidence(
        db,
        product_names=["ELDENRING", "eldenringdx12"],
    )

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(
            duplicate_auto_merge=True,
            duplicate_similarity_threshold=0.95,
        )
    )
    strict_duplicate_groups = db.count_duplicate_title_groups()

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(
            duplicate_auto_merge=True,
            duplicate_similarity_threshold=0.75,
        )
    )

    assert strict_duplicate_groups == 1
    assert db.count_duplicate_title_groups() == 0


def test_rebuild_uses_configured_minimum_evidence_confidence(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    _seed_low_confidence_evidence(db)

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(minimum_evidence_confidence="low")
    )
    low_threshold_titles = db.load_snapshot(limit=10).coverage.tracked_titles

    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(minimum_evidence_confidence="medium")
    )

    assert low_threshold_titles == 1
    assert db.load_snapshot(limit=10).coverage.tracked_titles == 0


def _title(
    title_id: str,
    title: str,
    *,
    launches_confirmed: int = 0,
    launches_inferred: int = 0,
    launches_gui: int = 0,
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
            inferred=launches_inferred,
            gui=launches_gui,
            confidence=ConfidenceLevel.HIGH,
        ),
    )


def _seed_session_merge_edge_case(db: Database) -> None:
    scan_run_id = db.create_scan_run(["security_log"])
    observed_times = [
        datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 11, 18, 5, 0, tzinfo=timezone.utc),
    ]
    artifacts: list[RawArtifact] = []
    evidence: list[EvidenceRecord] = []
    for index, observed_at in enumerate(observed_times, start=1):
        artifact_id = f"artifact:start:{index}"
        artifacts.append(
            RawArtifact(
                artifact_id=artifact_id,
                scan_run_id=scan_run_id,
                source=SourceName.SECURITY_LOG,
                observed_at=observed_at,
                raw_ref=f"security_log:start:{index}",
                payload={
                    "pid": 4242,
                    "user_sid": "S-1-5-21-demo",
                    "exe_path": r"D:\Games\Balatro\balatro.exe",
                    "product_name": "Balatro",
                },
            )
        )
        evidence.append(
            EvidenceRecord(
                evidence_id=f"evidence:start:{index}",
                artifact_id=artifact_id,
                source=SourceName.SECURITY_LOG,
                evidence_type=EvidenceType.PROCESS_START,
                observed_at=observed_at,
                strength=EvidenceStrength.EXACT,
                value={
                    "pid": 4242,
                    "user_sid": "S-1-5-21-demo",
                    "exe_path": r"D:\Games\Balatro\balatro.exe",
                    "product_name": "Balatro",
                },
            )
        )

    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)


def _seed_duplicate_evidence(db: Database, *, product_names: list[str]) -> None:
    scan_run_id = db.create_scan_run(["prefetch"])
    artifacts: list[RawArtifact] = []
    evidence: list[EvidenceRecord] = []
    for index, product_name in enumerate(product_names, start=1):
        exe_name = f"{product_name.lower().replace(' ', '')}-{index}"
        artifact_id = f"artifact:dup:{index}"
        exe_path = rf"D:\Games\{exe_name}\{exe_name}.exe"
        artifacts.append(
            RawArtifact(
                artifact_id=artifact_id,
                scan_run_id=scan_run_id,
                source=SourceName.PREFETCH,
                observed_at=datetime(2026, 4, 11, 18, index, 0, tzinfo=timezone.utc),
                raw_ref=f"prefetch:{exe_name.upper()}.EXE",
                payload={
                    "exe_path": exe_path,
                    "product_name": product_name,
                },
            )
        )
        evidence.append(
            EvidenceRecord(
                evidence_id=f"evidence:dup:{index}",
                artifact_id=artifact_id,
                source=SourceName.PREFETCH,
                evidence_type=EvidenceType.RECENT_EXECUTION,
                observed_at=datetime(2026, 4, 11, 18, index, 0, tzinfo=timezone.utc),
                strength=EvidenceStrength.STRONG,
                value={
                    "exe_path": exe_path,
                    "product_name": product_name,
                },
            )
        )

    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)


def _seed_low_confidence_evidence(db: Database) -> None:
    scan_run_id = db.create_scan_run(["bam"])
    artifact = RawArtifact(
        artifact_id="artifact:weak:1",
        scan_run_id=scan_run_id,
        source=SourceName.BAM,
        observed_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        raw_ref=r"bam:D:\Games\WeakGame\weakgame.exe",
        payload={
            "exe_path": r"D:\Games\WeakGame\weakgame.exe",
            "product_name": "Weak Game",
        },
    )
    evidence = EvidenceRecord(
        evidence_id="evidence:weak:1",
        artifact_id=artifact.artifact_id,
        source=SourceName.BAM,
        evidence_type=EvidenceType.RECENT_EXECUTION,
        observed_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        strength=EvidenceStrength.WEAK,
        value={
            "exe_path": r"D:\Games\WeakGame\weakgame.exe",
            "product_name": "Weak Game",
        },
    )
    db.replace_artifacts_for_scan(scan_run_id, [artifact])
    db.replace_evidence_for_scan(scan_run_id, [evidence])
