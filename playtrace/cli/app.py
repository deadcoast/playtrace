from __future__ import annotations

import typer

from playtrace.cli.cmd_doctor import register_doctor
from playtrace.cli.cmd_export import register_export
from playtrace.cli.cmd_inspect import register_inspect
from playtrace.cli.cmd_map import register_map
from playtrace.cli.cmd_report import register_report
from playtrace.cli.cmd_scan import register_scan
from playtrace.cli.cmd_sessions import register_sessions
from playtrace.cli.cmd_sources import register_sources
from playtrace.cli.cmd_titles import register_titles
<<<<<<< HEAD

from playtrace.services.doctor import DoctorRequest, DoctorService
from playtrace.services.reporter import ReportRequest, ReporterService
from playtrace.services.scanner import ScanRequest, ScannerService
=======
>>>>>>> 5826d2c01e206f624bf2fa0731bedd097ed65711

app = typer.Typer(
    help="Native Windows executable history and session analysis.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

<<<<<<< HEAD

@app.command("doctor")
def doctor(
    db: Path = typer.Option(Path("playtrace.db"), "--db", help="Path to the playtrace SQLite database."),
    theme: str = typer.Option("midnight", "--theme", help="Theme name: midnight, amber, ice, mono."),
) -> None:
    """Check local environment and data-source availability."""
    request = DoctorRequest(db_path=db, theme=theme)
    DoctorService().render(request)


@app.command("scan")
def scan(
    db: Path = typer.Option(Path("playtrace.db"), "--db", help="Path to the playtrace SQLite database."),
    days: int = typer.Option(
        30,
        "--days",
        min=1,
        max=365,
        help="How many days of Security log history to scan.",
    ),
    theme: str = typer.Option("midnight", "--theme", help="Theme name: midnight, amber, ice, mono."),
) -> None:
    """Ingest historical sessions from the Windows Security log."""
    request = ScanRequest(db_path=db, days=days, theme=theme)
    ScannerService().run(request)

@app.command("doctor")
def doctor(
    db: Path = typer.Option(Path("playtrace.db"), "--db", help="Path to the playtrace SQLite database."),
    theme: str = typer.Option("midnight", "--theme", help="Theme name: midnight, amber, ice, mono."),
) -> None:
    """Check local environment and data-source availability."""
    request = DoctorRequest(db_path=db, theme=theme)
    DoctorService().render(request)


@app.command("report")
def report(
    db: Path = typer.Option(Path("playtrace.db"), "--db", help="Path to the playtrace SQLite database."),
    theme: str = typer.Option("midnight", "--theme", help="Theme name: midnight, amber, ice, mono."),
    density: str = typer.Option("comfortable", "--density", help="Density mode: compact, comfortable, cinematic."),
    limit: int = typer.Option(10, "--limit", min=1, help="Number of top titles to display."),
) -> None:
    """Render the default playtrace dashboard."""
    request = ReportRequest(db_path=db, theme=theme, density=density, limit=limit)
    ReporterService().render_default(request)

=======
>>>>>>> 5826d2c01e206f624bf2fa0731bedd097ed65711
register_scan(app)
register_report(app)
register_titles(app)
register_sessions(app)
register_inspect(app)
register_sources(app)
register_map(app)
register_doctor(app)
register_export(app)
