from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawSessionsInput, UNSET
from playtrace.services.reporter import SessionsRequest, ReporterService


def register_sessions(app: typer.Typer) -> None:
    @app.command("sessions")
    def sessions(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
        density: DensityOption = None,
        title: str | None = typer.Option(None, "--title", help="Filter sessions by title."),
        days: int | None = typer.Option(None, "--days", min=1, help="Recent day window."),
        limit: int | None = typer.Option(None, "--limit", min=1),
    ) -> None:
        request = SessionsRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            raw=RawSessionsInput(
                theme=theme if theme is not None else UNSET,
                density=density if density is not None else UNSET,
                title=title if title is not None else UNSET,
                days=days if days is not None else UNSET,
                limit=limit if limit is not None else UNSET,
            ),
        )
        ReporterService().render_sessions(request)
