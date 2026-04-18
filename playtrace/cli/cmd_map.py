from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, SpecOption
from playtrace.config.runtime import RawMapInput, UNSET
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
        auto: bool | None = typer.Option(
            None,
            "--auto/--no-auto",
            help="Aggressively merge suspected duplicate titles.",
        ),
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
    ) -> None:
        request = MapRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            raw=RawMapInput(auto=auto if auto is not None else UNSET),
            target=target,
            title=title,
            classification=classification,
            launcher=launcher,
            ignore=ignore,
        )
        try:
            merged = MapperService().apply(request)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

        if auto:
            typer.echo(f"Auto-merged {merged} duplicate title group(s).")
        else:
            typer.echo("Mapping applied.")
