from __future__ import annotations

from rich.text import Text


def confidence_badge(level: str) -> Text:
    styles = {
        "high": "black on green",
        "medium": "black on yellow",
        "low": "white on red",
        "unknown": "white on bright_black",
    }
    return Text(f" {level.upper()} ", style=styles.get(level, styles["unknown"]))
