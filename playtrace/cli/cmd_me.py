from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, ThemeOption
from playtrace.services.dashboard import DashboardRequest, DashboardService


def register_me(app: typer.Typer) -> None:
    @app.command("me", help="Render the identity dashboard from stored data, optionally refreshing first.")
    def me(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        refresh: bool = typer.Option(False, "--refresh", help="Run a fresh scan before rendering."),
    ) -> None:
        request = DashboardRequest(db_path=db, refresh=refresh, theme=theme)
        DashboardService().render(request)
