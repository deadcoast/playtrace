from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.inspector import InspectRequest, InspectorService


def register_inspect(app: typer.Typer) -> None:
    @app.command("inspect")
    def inspect(
        target: str = typer.Argument(..., help="Title name, executable path, or internal ID."),
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
    ) -> None:
        request = InspectRequest(db_path=db, theme=theme, density=density, target=target)
        InspectorService().render(request)