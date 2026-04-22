from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from playtrace.models.report import ReportSnapshot
from playtrace.render.cards import metric_cards
from playtrace.render.tables import (
    UNKNOWN_LABEL,
    duplicate_candidates_table,
    format_duration,
    sessions_table,
    titles_table,
)
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
                (
                    "Confirmed Runtime",
                    _confirmed_runtime_value(snapshot),
                    "exact session-backed",
                ),
                ("Confirmed Sessions", str(coverage.confirmed_sessions), "merged activity windows"),
                ("Unmapped", str(coverage.unmapped_executables), "executables needing review"),
            ],
        )
    )

    console.print()
    console.print(Text("Top Titles", style=f"bold {theme.text}"))
    console.print(titles_table(snapshot.top_titles))
    if not snapshot.top_titles:
        console.print(Text("No titles have been reconstructed yet.", style=theme.dim))

    console.print()
    console.print(Text("Recent Sessions", style=f"bold {theme.text}"))
    console.print(
        sessions_table(list(zip(snapshot.recent_session_titles, snapshot.recent_sessions, strict=False)))
    )
    if not snapshot.recent_sessions:
        console.print(Text("No sessions have been reconstructed yet.", style=theme.dim))

    if snapshot.duplicate_candidates:
        console.print()
        console.print(Text("Duplicate Candidates", style=f"bold {theme.text}"))
        console.print(duplicate_candidates_table(snapshot.duplicate_candidates))

    if snapshot.warnings:
        console.print()
        warning_text = Text()
        for line in snapshot.warnings:
            warning_text.append(f"- {line}\n", style=theme.warning)
        console.print(Panel(warning_text, title="Warnings", border_style=theme.warning, padding=(1, 2)))


def render_titles_view(
    console: Console,
    theme: Theme,
    *,
    titles,
    sort_by: str,
    classification: str | None,
    launcher: str | None,
) -> None:
    header = Text()
    header.append("playtrace TITLES\n", style=f"bold {theme.accent}")
    header.append(
        f"Sort: {sort_by}    Classification: {classification or 'all'}    "
        f"Launcher: {launcher or 'all'}",
        style=theme.dim,
    )
    console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))
    console.print(titles_table(titles))
    if not titles:
        console.print(Text("No titles matched the current filters.", style=theme.dim))


def render_sessions_view(
    console: Console,
    theme: Theme,
    *,
    sessions,
    days: int,
    title_filter: str | None,
) -> None:
    header = Text()
    header.append("playtrace SESSIONS\n", style=f"bold {theme.accent}")
    header.append(
        f"Days: {days}    Title filter: {title_filter or 'all'}",
        style=theme.dim,
    )
    console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))
    console.print(sessions_table(sessions))
    if not sessions:
        console.print(Text("No sessions matched the current filters.", style=theme.dim))


def _confirmed_runtime_value(snapshot: ReportSnapshot) -> str:
    coverage = snapshot.coverage
    if (
        coverage.confirmed_runtime_seconds <= 0
        and coverage.confirmed_sessions <= 0
        and coverage.tracked_titles > 0
    ):
        return UNKNOWN_LABEL
    return format_duration(coverage.confirmed_runtime_seconds)
