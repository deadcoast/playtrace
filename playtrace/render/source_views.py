from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing import TYPE_CHECKING

from playtrace.render.theme import Theme

if TYPE_CHECKING:
    from playtrace.services.inspector import InspectionDetail
    from playtrace.services.sources import SourcesSnapshot


def render_sources(console: Console, theme: Theme, snapshot: SourcesSnapshot) -> None:
    console.print(Panel(Text(f"Sources for {snapshot.target}", style=f"bold {theme.accent}"), border_style=theme.accent))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Source")
    table.add_column("Evidence")
    table.add_column("Strength")
    table.add_column("Observed")
    table.add_column("Reference")

    for entry in snapshot.entries:
        table.add_row(
            entry.source,
            entry.evidence_type,
            entry.strength,
            entry.observed_at or "—",
            entry.raw_ref,
        )

    console.print(table)


def render_inspection(console: Console, theme: Theme, detail: InspectionDetail) -> None:
    body = Text()
    body.append(f"{detail.title}\n", style=f"bold {theme.accent}")
    body.append(f"Runtime confidence: {detail.runtime_confidence}\n", style=theme.text)
    body.append(
        f"Evidence sources: {', '.join(detail.evidence_sources) if detail.evidence_sources else 'none'}\n",
        style=theme.text,
    )
    body.append(
        f"Parent chains: {detail.parent_chains if detail.parent_chains else 'none'}",
        style=theme.text,
    )
    console.print(Panel(body, border_style=theme.accent))
