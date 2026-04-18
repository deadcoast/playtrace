from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawSourcesInput, UNSET
from playtrace.services.sources import SourcesRequest, SourcesService


def register_sources(app: typer.Typer) -> None:
    @app.command("sources")
    def sources(
        target: str = typer.Argument(..., help="Title, executable path, or internal ID."),
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
    ) -> None:
        request = SourcesRequest(
            db_path=db,
            target=target,
            config_path=config,
            spec_name=spec,
            raw=RawSourcesInput(theme=theme if theme is not None else UNSET),
        )
        SourcesService().render(request)
