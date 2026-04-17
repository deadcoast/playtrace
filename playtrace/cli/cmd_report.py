from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import ReportRequest, ReporterService


def register_report(app: typer.Typer) -> None:
    @app.command("report")
    def report(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        limit: int = typer.Option(10, "--limit", min=1, help="Number of top titles to display."),
        duplicates: bool = typer.Option(False, "--duplicates", help="Surface suspected duplicate title groups."),
    ) -> None:
        request = ReportRequest(
            db_path=db,
            config_path=config,
            theme=theme,
            density=density,
            limit=limit,
            show_duplicates=duplicates,
        )
        ReporterService().render_default(request)
