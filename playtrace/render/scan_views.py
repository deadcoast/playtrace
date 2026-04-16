from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from playtrace.render.cards import metric_cards
from playtrace.render.theme import Theme

if TYPE_CHECKING:
    from rich.console import Console

    from playtrace.services.scanner import ScanLiveSnapshot


STATUS_STYLES = {
    "ready": "success",
    "collected": "success",
    "empty": "dim",
    "unavailable": "warning",
    "collect_failed": "danger",
    "parse_failed": "danger",
    "pending": "dim",
}


def render_scan(console: Console, theme: Theme, snapshot: ScanLiveSnapshot) -> None:
    header = Text()
    header.append("playtrace SCAN\n", style=f"bold {theme.accent}")
    header.append(
        f"Completed: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S')}    Host: {snapshot.host_name}",
        style=theme.dim,
    )
    console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))
    console.print()
    console.print(Text("Summary", style=f"bold {theme.text}"))

    console.print(
        metric_cards(
            theme,
            [
                (
                    "Sources",
                    f"{snapshot.summary.completed_sources}/{snapshot.summary.total_sources}",
                    "collected or parsed without blocking",
                ),
                ("Artifacts", str(snapshot.summary.total_artifacts), "raw collector payloads stored"),
                ("Evidence", str(snapshot.summary.total_evidence), "typed records reconstructed"),
                (
                    "Titles",
                    str(snapshot.summary.tracked_titles),
                    (
                        f"{snapshot.summary.confirmed_sessions} sessions, "
                        f"{snapshot.summary.unmapped_executables} unmapped"
                    ),
                ),
            ],
        )
    )

    console.print()
    console.print(_source_status_table(theme, snapshot))

    if snapshot.warnings:
        warning_text = Text()
        for line in snapshot.warnings:
            warning_text.append(f"• {line}\n", style=theme.warning)
        console.print()
        console.print(Panel(warning_text, title="Warnings", border_style=theme.warning, padding=(1, 2)))


def _source_status_table(theme: Theme, snapshot: ScanLiveSnapshot) -> Table:
    table = Table(title="Source Status", show_header=True, header_style=f"bold {theme.text}")
    table.add_column("Source")
    table.add_column("Status")
    table.add_column("Artifacts", justify="right")
    table.add_column("Evidence", justify="right")
    table.add_column("Notes", ratio=2)

    for status in snapshot.sources:
        style_name = STATUS_STYLES.get(status.status, "dim")
        style = getattr(theme, style_name)
        notes = "; ".join(status.warnings) if status.warnings else "—"
        table.add_row(
            status.source,
            f"[{style}]{status.status.replace('_', ' ')}[/{style}]",
            str(status.artifacts),
            str(status.evidence),
            notes,
        )

    return table
