from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
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


def test_load_snapshot_includes_recent_sessions_and_unmapped_count(tmp_path: Path) -> None:
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
                launcher="Steam",
                runtime=RuntimeStats(
                    confirmed_seconds=600,
                    estimated_seconds=0,
                    foreground_seconds=540,
                    confidence=ConfidenceLevel.HIGH,
                ),
                launches=LaunchStats(
                    confirmed=1,
                    inferred=0,
                    gui=1,
                    confidence=ConfidenceLevel.HIGH,
                ),
                first_seen=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
                last_seen=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
                evidence_sources=["security_log", "prefetch"],
            )
        ]
    )
    db.replace_sessions(
        [
            SessionRecord(
                session_id="session:elden-ring:1",
                title_id="title:elden-ring",
                exe_id="exe:eldenring",
                user_sid="S-1-5-21-demo",
                started_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
                ended_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
                duration_seconds=600,
                foreground_seconds=540,
                confidence=RuntimeConfidence.EXACT,
                evidence_sources=["security_log", "prefetch"],
                evidence_ids=["evidence:start", "evidence:end"],
            )
        ]
    )
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO executables (
                exe_id, normalized_key, path, filename, original_filename, product_name,
                file_description, signer, company_name, sha1, classification,
                classification_confidence, ignored, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "exe:unmapped",
                "unmapped.exe",
                r"C:\Games\Unmapped\unmapped.exe",
                "unmapped.exe",
                "unmapped.exe",
                "Unmapped",
                None,
                None,
                None,
                None,
                Classification.UNKNOWN.value,
                ConfidenceLevel.UNKNOWN.value,
                0,
                datetime(2026, 4, 12, 8, 0, 0, tzinfo=timezone.utc).isoformat(),
                datetime(2026, 4, 12, 8, 0, 0, tzinfo=timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    snapshot = db.load_snapshot(limit=5)

    assert snapshot.coverage.unmapped_executables == 1
    assert snapshot.recent_sessions
    assert snapshot.recent_sessions[0].session_id == "session:elden-ring:1"


def test_load_snapshot_tolerates_legacy_nulls_and_invalid_confidence_values(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO titles (
                title_id, title, classification, classification_confidence, title_confidence,
                launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "title:legacy",
                "Legacy Title",
                "bad-classification",
                "bad-confidence",
                "bad-title-confidence",
                None,
                0,
                0,
                0,
                "bad-runtime",
                0,
                0,
                0,
                "bad-launches",
                None,
                None,
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
                "session:legacy:1",
                "title:legacy",
                "exe:legacy",
                None,
                datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc).isoformat(),
                None,
                None,
                0,
                0,
                0,
                "bad-runtime",
                "[]",
                "[]",
                "[]",
                "[]",
            ),
        )
        conn.commit()

    snapshot = db.load_snapshot(limit=5)

    assert snapshot.top_titles[0].classification is Classification.UNKNOWN
    assert snapshot.top_titles[0].classification_confidence is ConfidenceLevel.UNKNOWN
    assert snapshot.top_titles[0].runtime.confidence is ConfidenceLevel.UNKNOWN
    assert snapshot.recent_sessions[0].confidence is RuntimeConfidence.UNKNOWN
    assert snapshot.recent_sessions[0].foreground_seconds == 0
