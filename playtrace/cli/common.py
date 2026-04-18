from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

DatabaseOption = Annotated[
    Path,
    typer.Option(
        "--db",
        help="Path to the playtrace SQLite database.",
        dir_okay=False,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
]

ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        help="Optional path to a config file.",
        dir_okay=False,
        resolve_path=True,
    ),
]

SpecOption = Annotated[
    str | None,
    typer.Option("--spec", help="Optional power-user profile name."),
]

ThemeOption = Annotated[
    str | None,
    typer.Option("--theme", help="Theme name: midnight, amber, ice, mono."),
]

DensityOption = Annotated[
    str | None,
    typer.Option("--density", help="Density mode: compact, comfortable, cinematic."),
]
