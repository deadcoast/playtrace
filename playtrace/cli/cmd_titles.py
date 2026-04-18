from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawTitlesInput, UNSET
from playtrace.services.reporter import TitlesRequest, ReporterService


def register_titles(app: typer.Typer) -> None:
    @app.command("titles")
    def titles(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
        density: DensityOption = None,
        sort_by: str | None = typer.Option(None, "--sort", help="runtime, launches, last_seen, title"),
        classification: str | None = typer.Option(None, "--classification", help="Filter by title classification."),
        launcher: str | None = typer.Option(None, "--launcher", help="Filter by launcher."),
        limit: int | None = typer.Option(None, "--limit", min=1),
    ) -> None:
        request = TitlesRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            raw=RawTitlesInput(
                theme=theme if theme is not None else UNSET,
                density=density if density is not None else UNSET,
                sort_by=sort_by if sort_by is not None else UNSET,
                classification=classification if classification is not None else UNSET,
                launcher=launcher if launcher is not None else UNSET,
                limit=limit if limit is not None else UNSET,
            ),
        )
        ReporterService().render_titles(request)
