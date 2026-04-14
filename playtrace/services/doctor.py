from __future__ import annotations

import ctypes
import os
import platform
from dataclasses import dataclass
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from playtrace.render.console import build_console
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class DoctorRequest:
    db_path: Path
    theme: str


class DoctorService:
    def render(self, request: DoctorRequest) -> None:
        console = build_console()
        theme = get_theme(request.theme)

        db = Database(request.db_path)
        db.bootstrap()

        checks = {
            "Platform": platform.system(),
            "Windows": "yes" if os.name == "nt" else "no",
            "Administrator": "yes" if self._is_admin() else "no",
            "Database": str(request.db_path.resolve()),
            "Prefetch dir": self._exists(r"C:\Windows\Prefetch"),
            "SRUM DB": self._exists(r"C:\Windows\System32\sru\SRUDB.dat"),
            "Security log access": "unknown (parser not wired yet)",
            "UserAssist": "registry-backed (parser not wired yet)",
        }

        header = Text()
        header.append("playtrace DOCTOR\n", style=f"bold {theme.accent}")
        header.append("Environment and source-readiness checks", style=theme.dim)
        console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))

        table = Table(show_header=True, header_style="bold")
        table.add_column("Check", ratio=2)
        table.add_column("Status", ratio=3)

        for name, value in checks.items():
            table.add_row(name, str(value))

        console.print(table)

    def _exists(self, path: str) -> str:
        return "present" if Path(path).exists() else "missing"

    def _is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
