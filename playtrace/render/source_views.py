from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import TYPE_CHECKING

from playtrace.render.theme import Theme

if TYPE_CHECKING:
    from playtrace.services.inspector import InspectionDetail
    from playtrace.services.sources import SourcesSnapshot


def render_sources(console: Console, theme: Theme, snapshot: SourcesSnapshot) -> None:
    console.print(Panel(Text(f"Sources for {snapshot.target}", style=f"bold {theme.accent}"), border_style=theme.accent))
    if not snapshot.entries:
        console.print(Text("No evidence matched this target.", style=theme.dim))
    for index, entry in enumerate(snapshot.entries, start=1):
        body = Text()
        body.append(f"Source: {entry.source}\n", style=theme.text)
        body.append(f"Evidence: {entry.evidence_type}\n", style=theme.text)
        body.append(f"Strength: {entry.strength}\n", style=theme.text)
        body.append(f"Observed: {entry.observed_at or 'unknown'}\n", style=theme.text)
        body.append(f"Ref: {entry.raw_ref or '-'}\n", style=theme.text)
        body.append(f"Why: {entry.reasoning or 'unknown'}", style=theme.dim)
        console.print(
            Panel(
                body,
                title=f"Entry {index}",
                border_style=theme.dim,
                padding=(1, 2),
            )
        )
    if snapshot.conflicts:
        console.print(
            Panel(
                "\n".join(snapshot.conflicts),
                title="Conflicts",
                border_style=theme.warning,
            )
        )


def render_inspection(console: Console, theme: Theme, detail: InspectionDetail) -> None:
    body = Text()
    body.append(f"{detail.title}\n", style=f"bold {theme.accent}")
    body.append(f"Runtime confidence: {detail.runtime_confidence}\n", style=theme.text)
    body.append(
        f"Evidence sources: {', '.join(detail.evidence_sources) if detail.evidence_sources else 'none'}\n",
        style=theme.text,
    )
    body.append(
        "Evidence source counts: "
        f"{detail.evidence_source_counts if detail.evidence_source_counts else 'none'}\n",
        style=theme.text,
    )
    body.append(
        f"Evidence ids: {', '.join(detail.evidence_ids) if detail.evidence_ids else 'none'}\n",
        style=theme.text,
    )
    body.append(
        "Alternate titles: "
        f"{', '.join(detail.alternate_titles) if detail.alternate_titles else 'none'}\n",
        style=theme.text,
    )
    body.append(
        f"Parent chains: {detail.parent_chains if detail.parent_chains else 'none'}\n",
        style=theme.text,
    )
    body.append(f"Mapping source: {detail.mapping_source}\n", style=theme.text)
    body.append(
        "Confidence reasoning: "
        f"{' | '.join(detail.confidence_reasoning) if detail.confidence_reasoning else 'none'}",
        style=theme.text,
    )
    if detail.conflicts:
        body.append("\nConflicts: ", style=theme.text)
        body.append(" | ".join(detail.conflicts), style=theme.warning)
    console.print(Panel(body, border_style=theme.accent))
