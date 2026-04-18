from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from playtrace.cli.app import app
from playtrace.config.runtime import (
    UNSET,
    RawDoctorInput,
    RawMeInput,
    RawReportInput,
    RawScanInput,
)
from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.render.theme import get_theme
from playtrace.services.dashboard import DashboardRequest, DashboardService
from playtrace.services.doctor import DoctorRequest, DoctorService
from playtrace.services.reporter import ReportRequest, ReporterService
from playtrace.services.scanner import ScanRequest, ScannerService
from playtrace.store.db import Database


runner = CliRunner()


def test_scan_uses_config_default_sources_when_cli_sources_are_unset(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
[defaults]
default_sources = ["userassist"]
""",
    )

    snapshot = ScannerService(collectors=[], parsers=[]).run_for_snapshot(
        ScanRequest(
            db_path=tmp_path / "playtrace.db",
            config_path=config_path,
            spec_name=None,
            raw=RawScanInput(),
        )
    )

    assert snapshot.selected_sources == ["userassist"]


def test_dashboard_uses_config_refresh_when_cli_refresh_is_unset(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
[me]
refresh = true
""",
    )

    class FakeScannerService:
        def __init__(self) -> None:
            self.called = False

        def run(self, request: object) -> None:
            self.called = True

    service = DashboardService(scanner=FakeScannerService())
    service.load(
        DashboardRequest(
            db_path=tmp_path / "playtrace.db",
            config_path=config_path,
            spec_name=None,
            raw=RawMeInput(),
        )
    )

    assert service.scanner.called is True


def test_report_uses_config_limit_when_cli_limit_is_unset(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
[report]
limit = 1
""",
    )
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    db.replace_titles(
        [
            _title("title:alpha", "Alpha"),
            _title("title:bravo", "Bravo"),
        ]
    )

    snapshot = ReporterService().build_report_snapshot(
        ReportRequest(
            db_path=db.path,
            config_path=config_path,
            spec_name=None,
            raw=RawReportInput(),
        )
    )

    assert len(snapshot.top_titles) == 1


def test_report_cli_theme_overrides_config_theme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(
        tmp_path,
        """
[defaults]
theme = "amber"
""",
    )
    captured: list[str] = []

    def record_theme(name: str):
        captured.append(name)
        return get_theme(name)

    monkeypatch.setattr("playtrace.services.reporter.get_theme", record_theme)

    ReporterService().render_default(
        ReportRequest(
            db_path=tmp_path / "playtrace.db",
            config_path=config_path,
            spec_name=None,
            raw=RawReportInput(theme="mono"),
        )
    )

    assert captured[-1] == "mono"


def test_doctor_uses_config_theme_when_cli_theme_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(
        tmp_path,
        """
[defaults]
theme = "amber"
""",
    )
    captured: list[str] = []

    def record_theme(name: str):
        captured.append(name)
        return get_theme(name)

    monkeypatch.setattr("playtrace.services.doctor.get_theme", record_theme)

    DoctorService().render(
        DoctorRequest(
            db_path=tmp_path / "playtrace.db",
            config_path=config_path,
            spec_name=None,
            raw=RawDoctorInput(),
        )
    )

    assert captured[-1] == "amber"


def test_scan_command_preserves_unset_theme_and_density_for_config_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(tmp_path, "[defaults]\ntheme = \"amber\"\n")

    class SpyScannerService:
        def __init__(self) -> None:
            self.request = None

        def render(self, request: object) -> None:
            self.request = request

    spy = SpyScannerService()
    monkeypatch.setattr("playtrace.cli.cmd_scan.ScannerService", lambda: spy)

    result = runner.invoke(app, ["scan", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])

    assert result.exit_code == 0
    assert spy.request.config_path == config_path
    assert spy.request.raw.theme is UNSET
    assert spy.request.raw.density is UNSET


def test_me_command_accepts_config_and_preserves_unset_theme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(tmp_path, "[defaults]\ntheme = \"amber\"\n")

    class SpyDashboardService:
        def __init__(self) -> None:
            self.request = None

        def render(self, request: object) -> None:
            self.request = request

    spy = SpyDashboardService()
    monkeypatch.setattr("playtrace.cli.cmd_me.DashboardService", lambda: spy)

    result = runner.invoke(app, ["me", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])

    assert result.exit_code == 0
    assert spy.request.config_path == config_path
    assert spy.request.raw.theme is UNSET


def test_doctor_command_accepts_config_and_preserves_unset_theme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(tmp_path, "[defaults]\ntheme = \"amber\"\n")

    class SpyDoctorService:
        def __init__(self) -> None:
            self.request = None

        def render(self, request: object) -> None:
            self.request = request

    spy = SpyDoctorService()
    monkeypatch.setattr("playtrace.cli.cmd_doctor.DoctorService", lambda: spy)

    result = runner.invoke(app, ["doctor", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])

    assert result.exit_code == 0
    assert spy.request.config_path == config_path
    assert spy.request.raw.theme is UNSET


def test_titles_uses_config_limit_when_cli_limit_is_unset(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    config_path = write_config(tmp_path, "[titles]\nlimit = 1\n")
    _seed_titles_database(db_path, ["Alpha", "Bravo"])

    result = runner.invoke(app, ["titles", "--db", str(db_path), "--config", str(config_path), "--theme", "mono"])

    assert result.exit_code == 0
    assert "Alpha" in result.stdout
    assert "Bravo" not in result.stdout


def test_titles_cli_limit_overrides_config_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    config_path = write_config(tmp_path, "[titles]\nlimit = 1\n")
    _seed_titles_database(db_path, ["Alpha", "Bravo"])

    result = runner.invoke(
        app,
        [
            "titles",
            "--db",
            str(db_path),
            "--config",
            str(config_path),
            "--theme",
            "mono",
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "Alpha" in result.stdout
    assert "Bravo" in result.stdout


def test_sessions_uses_config_days_when_cli_days_is_unset(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    config_path = write_config(tmp_path, "[sessions]\ndays = 7\n")
    _seed_sessions_database(db_path)

    result = runner.invoke(app, ["sessions", "--db", str(db_path), "--config", str(config_path), "--theme", "mono"])

    assert result.exit_code == 0
    assert "Recent Game" in result.stdout
    assert "Old Game" not in result.stdout


def test_sessions_cli_days_override_config_days(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    config_path = write_config(tmp_path, "[sessions]\ndays = 7\n")
    _seed_sessions_database(db_path)

    result = runner.invoke(
        app,
        [
            "sessions",
            "--db",
            str(db_path),
            "--config",
            str(config_path),
            "--theme",
            "mono",
            "--days",
            "365",
        ],
    )

    assert result.exit_code == 0
    assert "Recent Game" in result.stdout
    assert "Old Game" in result.stdout


def test_export_uses_cli_format_over_config_format(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "out.json"
    config_path = write_config(tmp_path, "[export]\nformat = \"markdown\"\n")
    _seed_titles_database(db_path, ["Alpha"])

    result = runner.invoke(
        app,
        [
            "export",
            "--db",
            str(db_path),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").lstrip().startswith("{")


def test_map_uses_configured_auto_merge_posture_when_cli_auto_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(tmp_path, "[map]\nauto = true\n")

    class SpyMapperService:
        def __init__(self) -> None:
            self.request = None

        def apply(self, request: object) -> int:
            self.request = request
            return 1

    spy = SpyMapperService()
    monkeypatch.setattr("playtrace.cli.cmd_map.MapperService", lambda: spy)

    result = runner.invoke(app, ["map", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])

    assert result.exit_code == 0
    assert spy.request.raw.auto is UNSET
    assert spy.request.config_path == config_path


def test_map_cli_no_auto_overrides_config_auto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_config(tmp_path, "[map]\nauto = true\n")

    class SpyMapperService:
        def __init__(self) -> None:
            self.request = None

        def apply(self, request: object) -> int:
            self.request = request
            return 1

    spy = SpyMapperService()
    monkeypatch.setattr("playtrace.cli.cmd_map.MapperService", lambda: spy)

    result = runner.invoke(
        app,
        [
            "map",
            "example.exe",
            "--title",
            "Example",
            "--db",
            str(tmp_path / "playtrace.db"),
            "--config",
            str(config_path),
            "--no-auto",
        ],
    )

    assert result.exit_code == 0
    assert spy.request.raw.auto is False


def write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "playtrace.toml"
    path.write_text(body.strip(), encoding="utf-8")
    return path


def _title(title_id: str, title: str) -> TitleAggregate:
    return TitleAggregate(
        title_id=title_id,
        title=title,
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        runtime=RuntimeStats(
            confirmed_seconds=3600,
            estimated_seconds=0,
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


def _seed_titles_database(db_path: Path, titles: list[str]) -> None:
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            _title(f"title:{index}", title)
            for index, title in enumerate(titles, start=1)
        ]
    )


def _seed_sessions_database(db_path: Path) -> None:
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            _title("title:recent", "Recent Game"),
            _title("title:old", "Old Game"),
        ]
    )
    db.replace_sessions(
        [
            SessionRecord(
                session_id="session:recent",
                title_id="title:recent",
                exe_id="exe:recent",
                user_sid="S-1-5-21-demo",
                started_at=datetime(2026, 4, 16, 12, 0, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 4, 16, 12, 20, 0, tzinfo=timezone.utc),
                duration_seconds=1200,
                confidence=RuntimeConfidence.EXACT,
                evidence_sources=["security_log"],
            ),
            SessionRecord(
                session_id="session:old",
                title_id="title:old",
                exe_id="exe:old",
                user_sid="S-1-5-21-demo",
                started_at=datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 2, 1, 12, 20, 0, tzinfo=timezone.utc),
                duration_seconds=1200,
                confidence=RuntimeConfidence.EXACT,
                evidence_sources=["security_log"],
            ),
        ]
    )
