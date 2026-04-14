from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import SessionsRequest, ReporterService


def register_sessions(app: typer.Typer) -> None:
    @app.command("sessions")
    def sessions(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        title: str | None = typer.Option(None, "--title", help="Filter sessions by title."),
        days: int = typer.Option(30, "--days", min=1, help="Recent day window."),
        limit: int = typer.Option(100, "--limit", min=1),
    ) -> None:
        request = SessionsRequest(db_path=db, theme=theme, density=density, title=title, days=days, limit=limit)
        ReporterService().render_sessions(request)