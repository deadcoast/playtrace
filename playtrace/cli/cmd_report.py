from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawReportInput, UNSET
from playtrace.services.reporter import ReportRequest, ReporterService


def register_report(app: typer.Typer) -> None:
    @app.command("report")
    def report(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
        density: DensityOption = None,
        limit: int | None = typer.Option(None, "--limit", min=1, help="Number of top titles to display."),
        duplicates: bool = typer.Option(False, "--duplicates", help="Surface suspected duplicate title groups."),
    ) -> None:
        request = ReportRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            raw=RawReportInput(
                theme=theme if theme is not None else UNSET,
                density=density if density is not None else UNSET,
                limit=limit if limit is not None else UNSET,
            ),
            show_duplicates=duplicates,
        )
        ReporterService().render_default(request)
