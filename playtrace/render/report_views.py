from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from playtrace.models.report import ReportSnapshot
from playtrace.render.cards import metric_cards
from playtrace.render.tables import format_duration, titles_table
from playtrace.render.theme import Theme


def render_report(console: Console, theme: Theme, snapshot: ReportSnapshot) -> None:
    header = Text()
    header.append("playtrace REPORT\n", style=f"bold {theme.accent}")
    header.append(
        f"Snapshot: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S')}    Host: {snapshot.host_name}",
        style=theme.dim,
    )
    console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))

    coverage = snapshot.coverage
    console.print(
        metric_cards(
            theme,
            [
                ("Tracked Titles", str(coverage.tracked_titles), "games and apps surfaced"),
                ("Confirmed Runtime", format_duration(coverage.confirmed_runtime_seconds), "exact session-backed"),
                ("Confirmed Sessions", str(coverage.confirmed_sessions), "merged activity windows"),
                ("Unmapped", str(coverage.unmapped_executables), "executables needing review"),
            ],
        )
    )

    console.print()
    console.print(Text("Top Titles", style=f"bold {theme.text}"))
    console.print(titles_table(snapshot.top_titles))

    if snapshot.warnings:
        console.print()
        warning_text = Text()
        for line in snapshot.warnings:
            warning_text.append(f"• {line}\n", style=theme.warning)
        console.print(Panel(warning_text, title="Warnings", border_style=theme.warning, padding=(1, 2)))
