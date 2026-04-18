from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawInspectInput, UNSET
from playtrace.services.inspector import InspectRequest, InspectorService


def register_inspect(app: typer.Typer) -> None:
    @app.command("inspect")
    def inspect(
        target: str = typer.Argument(..., help="Title name, executable path, or internal ID."),
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
        density: DensityOption = None,
    ) -> None:
        request = InspectRequest(
            db_path=db,
            target=target,
            config_path=config,
            spec_name=spec,
            raw=RawInspectInput(
                theme=theme if theme is not None else UNSET,
                density=density if density is not None else UNSET,
            ),
        )
        InspectorService().render(request)
