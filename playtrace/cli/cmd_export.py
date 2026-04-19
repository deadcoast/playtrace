from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, SpecOption
from playtrace.config.runtime import RawExportInput, UNSET
from playtrace.services.exporter import ExportRequest, ExporterService


def register_export(app: typer.Typer) -> None:
    @app.command("export")
    def export(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        output: Path = typer.Option(..., "--output", help="Destination file path."),
        format: str | None = typer.Option(None, "--format", help="json, csv, markdown"),
        scope: str | None = typer.Option(
            None,
            "--scope",
            help="entity, lineage, repair-preview",
        ),
    ) -> None:
        request = ExportRequest(
            db_path=db,
            output_path=output,
            config_path=config,
            spec_name=spec,
            raw=RawExportInput(
                format=format if format is not None else UNSET,
                scope=scope if scope is not None else UNSET,
            ),
        )
        ExporterService().run(request)
