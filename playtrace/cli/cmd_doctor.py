from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, ThemeOption
from playtrace.services.doctor import DoctorRequest, DoctorService


def register_doctor(app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
    ) -> None:
        request = DoctorRequest(db_path=db, theme=theme)
        DoctorService().render(request)