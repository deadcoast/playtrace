from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, ThemeOption
from playtrace.services.sources import SourcesRequest, SourcesService


def register_sources(app: typer.Typer) -> None:
    @app.command("sources")
    def sources(
        target: str = typer.Argument(..., help="Title, executable path, or internal ID."),
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
    ) -> None:
        request = SourcesRequest(db_path=db, target=target, theme=theme)
        SourcesService().render(request)
