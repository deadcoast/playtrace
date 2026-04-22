from __future__ import annotations

from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

from playtrace.models.dashboard import IdentityDashboardSnapshot
from playtrace.render.cards import metric_cards
from playtrace.render.tables import UNKNOWN_LABEL, format_duration, titles_table
from playtrace.render.theme import Theme


ASCII_MARK = r"""
   ___  __           __
  / _ \/ /__ ___  __/ /_________ ________
 / ___/ / _ `/ / / / __/ __/ _ `/ __/ -_)
/_/  /_/\_,_/\_, /\__/_/  \_,_/\__/\__/
            /___/
""".strip("\n")


def render_dashboard(console, theme: Theme, snapshot: IdentityDashboardSnapshot) -> None:
    header = Columns(
        [
            Panel(Text(ASCII_MARK, style=f"bold {theme.accent}"), border_style=theme.accent, padding=(1, 2)),
            _identity_panel(theme, snapshot),
        ],
        equal=False,
        expand=True,
    )
    console.print(header)
    console.print()
    console.print(Text("Coverage", style=f"bold {theme.text}"))
    console.print(
        metric_cards(
            theme,
            [
                ("Tracked Titles", str(snapshot.coverage.tracked_titles), "reconstructed titles"),
                ("Confirmed Runtime", _confirmed_runtime_value(snapshot), "exact runtime"),
                ("Sessions", str(snapshot.coverage.confirmed_sessions), "reconstructed windows"),
                ("Unmapped", str(snapshot.coverage.unmapped_executables), "needs mapping"),
            ],
        )
    )
    console.print()
    console.print(Text("Top Titles", style=f"bold {theme.text}"))
    console.print(titles_table(snapshot.top_titles))
    if not snapshot.top_titles:
        console.print(Text("No titles have been reconstructed yet.", style=theme.dim))

    if snapshot.warnings:
        body = Text()
        for line in snapshot.warnings:
            body.append(f"- {line}\n", style=theme.warning)
        console.print()
        console.print(Panel(body, title="Audit Notes", border_style=theme.warning, padding=(1, 2)))


def _identity_panel(theme: Theme, snapshot: IdentityDashboardSnapshot) -> Panel:
    body = Text()
    body.append("playtrace ME\n", style=f"bold {theme.accent}")
    body.append(f"Host: {snapshot.host_name}\n", style=theme.text)
    body.append(f"Snapshot: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n", style=theme.text)
    body.append(f"Last scan: {snapshot.scan_age}", style=theme.dim)
    return Panel(body, border_style=theme.accent, padding=(1, 2))


def _confirmed_runtime_value(snapshot: IdentityDashboardSnapshot) -> str:
    if (
        snapshot.coverage.confirmed_runtime_seconds <= 0
        and snapshot.coverage.confirmed_sessions <= 0
        and snapshot.coverage.tracked_titles > 0
    ):
        return UNKNOWN_LABEL
    return format_duration(snapshot.coverage.confirmed_runtime_seconds)
