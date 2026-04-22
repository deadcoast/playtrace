from __future__ import annotations

from io import StringIO
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.report import CoverageSummary, ReportSnapshot
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.render.report_views import render_report, render_titles_view
from playtrace.render.theme import get_theme
from playtrace.services.reporter import ReportRequest, ReporterService, SessionsRequest, TitlesRequest
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


def test_render_report_shows_recent_sessions_without_placeholders(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles([_title(title_id="title:balatro", title="Balatro")])
    db.replace_sessions(
        [
            _session(
                session_id="session:recent",
                title_id="title:balatro",
                exe_id="path:d:\\games\\balatro\\balatro.exe",
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
                confidence=RuntimeConfidence.EXACT,
            )
        ]
    )

    ReporterService().render_default(
        ReportRequest(
            db_path=db_path,
            config_path=None,
            theme="mono",
            density="comfortable",
            limit=5,
        )
    )

    output = capsys.readouterr().out

    assert "Recent Sessions" in output
    assert "Balatro" in output


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


def test_render_titles_counts_gui_launches_in_total(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            _title(
                title_id="title:balatro",
                title="Balatro",
                confirmed_seconds=7200,
                estimated_seconds=0,
                launches_confirmed=0,
                launches_inferred=0,
                launches_gui=2,
            )
        ]
    )

    ReporterService().render_titles(
        TitlesRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            sort_by="runtime",
            classification=None,
            launcher=None,
            limit=10,
        )
    )

    output = capsys.readouterr().out

    assert "Balatro" in output
    assert "│        2 │" in output


def test_render_views_use_unknown_runtime_and_ascii_safe_placeholders() -> None:
    long_title = "PowertoysUserSetup-0.95.0-wix-bootstrap-long-name"
    title = _title(
        title_id="title:powertoys-bootstrap",
        title=long_title,
        launcher=None,
        confirmed_seconds=0,
        estimated_seconds=0,
        launches_confirmed=0,
        launches_inferred=0,
        launches_gui=1,
    )
    title.runtime.confidence = ConfidenceLevel.UNKNOWN
    snapshot = ReportSnapshot(
        generated_at=datetime(2026, 4, 22, 9, 58, 37, tzinfo=timezone.utc),
        host_name="homeone",
        coverage=CoverageSummary(
            tracked_titles=1,
            confirmed_runtime_seconds=0,
            estimated_runtime_seconds=0,
            confirmed_sessions=0,
            unmapped_executables=1,
        ),
        top_titles=[title],
        warnings=["Runtime evidence is incomplete."],
    )
    theme = get_theme("mono")

    report_buffer = StringIO()
    report_console = Console(file=report_buffer, width=52, color_system=None, force_terminal=False)
    render_report(report_console, theme, snapshot)
    report_output = report_buffer.getvalue()

    assert "UNKNOWN" in report_output
    assert "0h 00m" not in report_output
    assert "•" not in report_output
    assert "—" not in report_output
    assert "…" not in report_output

    titles_buffer = StringIO()
    titles_console = Console(file=titles_buffer, width=52, color_system=None, force_terminal=False)
    render_titles_view(
        titles_console,
        theme,
        titles=[title],
        sort_by="runtime",
        classification=None,
        launcher=None,
    )
    titles_output = titles_buffer.getvalue()

    assert "UNKNOWN" in titles_output
    assert "0h 00m" not in titles_output
    assert "—" not in titles_output
    assert "…" not in titles_output

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


def test_render_sessions_defaults_invalid_confidence_to_unknown(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    db.replace_titles([_title(title_id="title:balatro", title="Balatro")])
    db.replace_sessions(
        [
            _session(
                session_id="session:legacy-confidence",
                title_id="title:balatro",
                exe_id="path:d:\\games\\balatro\\balatro.exe",
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
                confidence=RuntimeConfidence.EXACT,
            )
        ]
    )
    with db.connect() as conn:
        conn.execute(
            "UPDATE sessions SET confidence = ? WHERE session_id = ?",
            ("legacy", "session:legacy-confidence"),
        )
        conn.commit()

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
    assert "UNKNOWN" in output


def test_render_sessions_displays_open_session_runtime_as_unknown(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    db.replace_titles([_title(title_id="title:balatro", title="Balatro")])
    db.replace_sessions(
        [
            _session(
                session_id="session:open",
                title_id="title:balatro",
                exe_id="path:d:\\games\\balatro\\balatro.exe",
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                ended_at=None,
                confidence=RuntimeConfidence.UNKNOWN,
            )
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
    assert "0h 00m" not in output


def test_render_report_duplicates_flag_surfaces_candidate_groups(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            _title(title_id="title:elden-ring", title="ELDEN RING"),
            _title(title_id="title:eldenring", title="eldenring"),
        ]
    )

    ReporterService().render_default(
        ReportRequest(
            db_path=db_path,
            config_path=None,
            theme="mono",
            density="comfortable",
            limit=5,
            show_duplicates=True,
        )
    )

    output = capsys.readouterr().out

    assert "Duplicate Candidates" in output


def _title(
    *,
    title_id: str,
    title: str,
    classification: Classification = Classification.GAME,
    launcher: str | None = "Steam",
    confirmed_seconds: int = 3600,
    estimated_seconds: int = 0,
    launches_confirmed: int = 1,
    launches_inferred: int = 0,
    launches_gui: int = 1,
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
            confirmed=launches_confirmed,
            inferred=launches_inferred,
            gui=launches_gui,
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
    ended_at: datetime | None,
    confidence: RuntimeConfidence,
) -> SessionRecord:
    duration_seconds = None
    if ended_at is not None:
        duration_seconds = int((ended_at - started_at).total_seconds())

    return SessionRecord(
        session_id=session_id,
        title_id=title_id,
        exe_id=exe_id,
        user_sid="S-1-5-21-demo",
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        foreground_seconds=1800,
        bytes_in=0,
        bytes_out=0,
        confidence=confidence,
        evidence_sources=["security_log"],
        evidence_ids=["evidence:1"],
        parent_chain=["steam.exe"],
        notes=[],
    )
