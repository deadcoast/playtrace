from __future__ import annotations

from rich.table import Table

from playtrace.models.title import TitleAggregate
from playtrace.render.badges import confidence_badge


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(seconds, 0), 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes:02d}m"


def titles_table(titles: list[TitleAggregate]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Title", ratio=3)
    table.add_column("Runtime", justify="right")
    table.add_column("Launches", justify="right")
    table.add_column("Confidence")
    table.add_column("Launcher")

    for title in titles:
        total_runtime = title.runtime.confirmed_seconds + title.runtime.estimated_seconds
        launches = title.launches.confirmed + title.launches.inferred
        table.add_row(
            title.title,
            format_duration(total_runtime),
            str(launches),
            confidence_badge(title.runtime.confidence.value),
            title.launcher or "—",
        )

    return table
