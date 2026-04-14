from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    accent: str
    success: str
    warning: str
    danger: str
    dim: str
    text: str


THEMES: dict[str, Theme] = {
    "midnight": Theme("midnight", "cyan", "green", "yellow", "red", "bright_black", "white"),
    "amber": Theme("amber", "bright_yellow", "green", "yellow", "red", "bright_black", "white"),
    "ice": Theme("ice", "bright_cyan", "green", "yellow", "red", "bright_black", "white"),
    "mono": Theme("mono", "white", "white", "white", "white", "bright_black", "white"),
}


def get_theme(name: str) -> Theme:
    return THEMES.get(name, THEMES["midnight"])
