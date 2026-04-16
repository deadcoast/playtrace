from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.services.reporter import (
    ReportRequest,
    ReporterService,
    SessionsRequest,
    TitlesRequest,
)
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


def test_render_titles_outputs_filtered_titles(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            _title(
                title_id="title:balatro",
                title="Balatro",
                classification=Classification.GAME,
                launcher="Steam",
                confirmed_seconds=7200,
                estimated_seconds=0,
            ),
            _title(
                title_id="title:discord",
                title="Discord",
                classification=Classification.HELPER,
                launcher="Discord",
                confirmed_seconds=300,
                estimated_seconds=0,
            ),
        ]
    )

    ReporterService().render_titles(
        TitlesRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            sort_by="runtime",
            classification="game",
            launcher="Steam",
            limit=10,
        )
    )

    output = capsys.readouterr().out

    assert "Balatro" in output
    assert "Discord" not in output


def test_render_sessions_outputs_recent_sessions(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    db.replace_titles(
        [
            _title(title_id="title:balatro", title="Balatro"),
            _title(title_id="title:older", title="Older Game"),
        ]
    )
    db.replace_sessions(
        [
            _session(
                session_id="session:recent",
                title_id="title:balatro",
                exe_id="path:d:\\games\\balatro\\balatro.exe",
                started_at=datetime.now(timezone.utc) - timedelta(days=2),
                ended_at=datetime.now(timezone.utc) - timedelta(days=2) + timedelta(hours=1),
                confidence=RuntimeConfidence.EXACT,
            ),
            _session(
                session_id="session:old",
                title_id="title:older",
                exe_id="path:d:\\games\\older\\older.exe",
                started_at=datetime.now(timezone.utc) - timedelta(days=45),
                ended_at=datetime.now(timezone.utc) - timedelta(days=45) + timedelta(hours=1),
                confidence=RuntimeConfidence.ESTIMATED,
            ),
        ]
    )

    ReporterService().render_sessions(
        SessionsRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            title=None,
            days=30,
            limit=10,
        )
    )

    output = capsys.readouterr().out

    assert "Balatro" in output
    assert "Older Game" not in output


def _title(
    *,
    title_id: str,
    title: str,
    classification: Classification = Classification.GAME,
    launcher: str | None = "Steam",
    confirmed_seconds: int = 3600,
    estimated_seconds: int = 0,
) -> TitleAggregate:
    return TitleAggregate(
        title_id=title_id,
        title=title,
        classification=classification,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher=launcher,
        runtime=RuntimeStats(
            confirmed_seconds=confirmed_seconds,
            estimated_seconds=estimated_seconds,
            foreground_seconds=1800,
            confidence=ConfidenceLevel.HIGH,
        ),
        launches=LaunchStats(
            confirmed=1,
            inferred=0,
            gui=1,
            confidence=ConfidenceLevel.HIGH,
        ),
        first_seen=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc),
        evidence_sources=["security_log"],
        tags=[],
        notes=[],
    )


def _session(
    *,
    session_id: str,
    title_id: str | None,
    exe_id: str,
    started_at: datetime,
    ended_at: datetime,
    confidence: RuntimeConfidence,
) -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        title_id=title_id,
        exe_id=exe_id,
        user_sid="S-1-5-21-demo",
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=int((ended_at - started_at).total_seconds()),
        foreground_seconds=1800,
        bytes_in=0,
        bytes_out=0,
        confidence=confidence,
        evidence_sources=["security_log"],
        evidence_ids=["evidence:1"],
        parent_chain=["steam.exe"],
        notes=[],
    )
