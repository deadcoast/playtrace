from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption
from playtrace.services.mapper import MapRequest, MapperService


def register_map(app: typer.Typer) -> None:
    @app.command("map")
    def map_title(
        target: str = typer.Argument(..., help="Executable path or executable ID."),
        title: str = typer.Option(..., "--title", help="User-facing title to assign."),
        classification: str | None = typer.Option(None, "--classification", help="Optional forced classification."),
        launcher: str | None = typer.Option(None, "--launcher", help="Optional launcher label."),
        ignore: bool = typer.Option(False, "--ignore", help="Suppress this executable from reports."),
        db: DatabaseOption = Path("playtrace.db"),
    ) -> None:
        request = MapRequest(
            db_path=db,
            target=target,
            title=title,
            classification=classification,
            launcher=launcher,
            ignore=ignore,
        )
        MapperService().apply(request)