from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, ThemeOption
from playtrace.services.scanner import ScanRequest, ScannerService


def register_scan(app: typer.Typer) -> None:
    @app.command("scan")
    def scan(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        sources: list[str] = typer.Option(
            None,
            "--source",
            help="Limit scan to one or more sources: security_log, prefetch, userassist, srum, amcache, bam.",
        ),
        full: bool = typer.Option(False, "--full", help="Force a full rescan."),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
    ) -> None:
        request = ScanRequest(
            db_path=db,
            config_path=config,
            sources=sources or [],
            full=full,
            theme=theme,
            density=density,
        )
        ScannerService().render(request)
