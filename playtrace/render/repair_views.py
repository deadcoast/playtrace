from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from playtrace.models.repair import RepairPreview
from playtrace.render.theme import Theme


def render_repair_preview(console: Console, theme: Theme, preview: RepairPreview, *, title: str) -> None:
    console.print(
        Panel(
            Text(title, style=f"bold {theme.accent}"),
            border_style=theme.accent,
        )
    )

    summary = Table(show_header=True, header_style="bold")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Merged titles", str(preview.counts.merged_titles))
    summary.add_row("Changed titles", str(preview.counts.changed_titles))
    summary.add_row("Changed sessions", str(preview.counts.changed_sessions))
    summary.add_row("Remaining duplicate groups", str(preview.counts.remaining_duplicate_groups))
    console.print(summary)

    for label, changes in [("Title Changes", preview.title_changes), ("Session Changes", preview.session_changes)]:
        console.print(
            Panel(
                Text("\n".join(changes) if changes else "No planned changes.", style=theme.text),
                title=label,
                border_style=theme.dim,
            )
        )
    if preview.unresolved:
        console.print(
            Panel(
                Text("\n".join(preview.unresolved), style=theme.warning),
                title="Unresolved",
                border_style=theme.warning,
            )
        )
