from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, SpecOption, ThemeOption
from playtrace.config.runtime import RawScanInput, UNSET
from playtrace.services.scanner import ScanRequest, ScannerService


def register_scan(app: typer.Typer) -> None:
    @app.command("scan")
    def scan(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        spec: SpecOption = None,
        sources: list[str] = typer.Option(
            None,
            "--source",
            help="Limit scan to one or more sources: security_log, prefetch, userassist, srum, amcache, bam.",
        ),
        full: bool | None = typer.Option(None, "--full/--no-full", help="Force a full rescan."),
        rebuild: bool = typer.Option(False, "--rebuild", help="Preview a reconstruction repair after scanning."),
        yes: bool = typer.Option(False, "--yes", help="Apply repair mutations after a rebuild preview."),
        theme: ThemeOption = None,
        density: DensityOption = None,
    ) -> None:
        request = ScanRequest(
            db_path=db,
            config_path=config,
            spec_name=spec,
            rebuild=rebuild,
            yes=yes,
            raw=RawScanInput(
                sources=list(sources) if sources else UNSET,
                full=full if full is not None else UNSET,
                theme=theme if theme is not None else UNSET,
                density=density if density is not None else UNSET,
            ),
        )
        ScannerService().render(request)
