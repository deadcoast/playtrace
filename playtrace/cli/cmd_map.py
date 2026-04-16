from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption
from playtrace.models.enums import Classification
from playtrace.services.mapper import MapRequest, MapperService


def register_map(app: typer.Typer) -> None:
    @app.command("map")
    def map_title(
        target: str | None = typer.Argument(None, help="Executable path or executable ID."),
        title: str | None = typer.Option(None, "--title", help="User-facing title to assign."),
        classification: Classification | None = typer.Option(
            None,
            "--classification",
            help="Optional forced classification.",
        ),
        launcher: str | None = typer.Option(None, "--launcher", help="Optional launcher label."),
        ignore: bool = typer.Option(False, "--ignore", help="Suppress this executable from reports."),
        auto: bool = typer.Option(False, "--auto", help="Aggressively merge suspected duplicate titles."),
        db: DatabaseOption = Path("playtrace.db"),
    ) -> None:
        if not auto and (not target or not title):
            raise typer.BadParameter("TARGET and --title are required unless --auto is used.")

        request = MapRequest(
            db_path=db,
            target=target,
            title=title,
            classification=classification,
            launcher=launcher,
            ignore=ignore,
            auto=auto,
        )
        merged = MapperService().apply(request)
        if auto:
            typer.echo(f"Auto-merged {merged} duplicate title group(s).")
        else:
            typer.echo("Mapping applied.")
