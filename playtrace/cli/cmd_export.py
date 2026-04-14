from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption
from playtrace.services.exporter import ExportRequest, ExporterService


def register_export(app: typer.Typer) -> None:
    @app.command("export")
    def export(
        db: DatabaseOption = Path("playtrace.db"),
        output: Path = typer.Option(..., "--output", help="Destination file path."),
        format: str = typer.Option("json", "--format", help="json, csv, markdown"),
    ) -> None:
        request = ExportRequest(db_path=db, output_path=output, format=format)
        ExporterService().run(request)