from __future__ import annotations

from rich.console import Console


def build_console() -> Console:
    return Console(highlight=False, soft_wrap=False)