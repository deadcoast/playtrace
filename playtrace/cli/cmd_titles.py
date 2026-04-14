from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import TitlesRequest, ReporterService


def register_titles(app: typer.Typer) -> None:
    @app.command("titles")
    def titles(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        sort_by: str = typer.Option("runtime", "--sort", help="runtime, launches, last_seen, title"),
        classification: str | None = typer.Option(None, "--classification", help="Filter by title classification."),
        launcher: str | None = typer.Option(None, "--launcher", help="Filter by launcher."),
        limit: int = typer.Option(50, "--limit", min=1),
    ) -> None:
        request = TitlesRequest(
            db_path=db,
            theme=theme,
            density=density,
            sort_by=sort_by,
            classification=classification,
            launcher=launcher,
            limit=limit,
        )
        ReporterService().render_titles(request)