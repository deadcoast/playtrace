from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawDoctorInput, UNSET
from playtrace.services.doctor import DoctorRequest, DoctorService


def register_doctor(app: typer.Typer) -> None:
    @app.command("doctor", help="Audit environment prerequisites and persisted data quality.")
    def doctor(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        repair: bool = typer.Option(False, "--repair", help="Preview a reconstruction repair plan."),
        yes: bool = typer.Option(False, "--yes", help="Apply repair mutations after a repair preview."),
        theme: ThemeOption = None,
    ) -> None:
        request = DoctorRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            repair=repair,
            yes=yes,
            raw=RawDoctorInput(theme=theme if theme is not None else UNSET),
        )
        DoctorService().render(request)
