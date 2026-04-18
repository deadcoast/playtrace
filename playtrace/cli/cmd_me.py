from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawMeInput, UNSET
from playtrace.services.dashboard import DashboardRequest, DashboardService


def register_me(app: typer.Typer) -> None:
    @app.command("me", help="Render the identity dashboard from stored data, optionally refreshing first.")
    def me(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        theme: ThemeOption = None,
        refresh: bool | None = typer.Option(
            None,
            "--refresh/--no-refresh",
            help="Run a fresh scan before rendering.",
        ),
    ) -> None:
        request = DashboardRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            raw=RawMeInput(
                refresh=refresh if refresh is not None else UNSET,
                theme=theme if theme is not None else UNSET,
            ),
        )
        DashboardService().render(request)
