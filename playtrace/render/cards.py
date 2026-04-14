from __future__ import annotations

from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

from playtrace.render.theme import Theme


def metric_cards(theme: Theme, cards: list[tuple[str, str, str]]) -> Columns:
    panels: list[Panel] = []
    for title, value, subtitle in cards:
        body = Text()
        body.append(f"{value}\n", style=f"bold {theme.accent}")
        body.append(subtitle, style=theme.dim)
        panels.append(Panel(body, title=title, border_style=theme.accent, padding=(1, 2)))
    return Columns(panels, equal=True, expand=True)
