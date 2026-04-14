from __future__ import annotations

import ctypes
import os
import platform
from dataclasses import dataclass, field
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


@dataclass(slots=True)
class DoctorSnapshot:
    exact_runtime_support: str
    supporting_sources: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)


class DoctorService:
    def load(self, request: DoctorRequest) -> DoctorSnapshot:
        db = Database(request.db_path)
        db.bootstrap()

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT source, evidence_type FROM evidence_links"
            ).fetchall()

        seen_sources = sorted({str(row["source"]) for row in rows})
        seen_types = {str(row["evidence_type"]) for row in rows}
        exact_runtime_support = (
            "available"
            if {"process_start", "process_exit"} <= seen_types
            else "unavailable"
        )
        supporting_sources = [
            source
            for source in seen_sources
            if source != "security_log"
        ]

        guidance: list[str] = []
        if exact_runtime_support == "available":
            guidance.append("Exact runtime is available from Security Log process start/exit evidence.")
        else:
            guidance.append("Exact runtime is not currently available; Playtrace will rely on inferred coverage.")

        if supporting_sources:
            guidance.append(
                f"Supporting evidence is available from: {', '.join(supporting_sources)}."
            )
        else:
            guidance.append("No supporting evidence sources have been ingested yet.")

        checks = {
            "Platform": platform.system(),
            "Windows": "yes" if os.name == "nt" else "no",
            "Administrator": "yes" if self._is_admin() else "no",
            "Database": str(request.db_path.resolve()),
            "Prefetch dir": self._exists(r"C:\Windows\Prefetch"),
            "SRUM DB": self._exists(r"C:\Windows\System32\sru\SRUDB.dat"),
            "Exact runtime support": exact_runtime_support,
        }

        return DoctorSnapshot(
            exact_runtime_support=exact_runtime_support,
            supporting_sources=supporting_sources,
            guidance=guidance,
            checks=checks,
        )

    def render(self, request: DoctorRequest) -> None:
        console = build_console()
        theme = get_theme(request.theme)
        snapshot = self.load(request)

        header = Text()
        header.append("playtrace DOCTOR\n", style=f"bold {theme.accent}")
        header.append("Coverage and source-readiness checks", style=theme.dim)
        console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))

        table = Table(show_header=True, header_style="bold")
        table.add_column("Check", ratio=2)
        table.add_column("Status", ratio=3)
        for name, value in snapshot.checks.items():
            table.add_row(name, str(value))
        console.print(table)

        guidance = Text()
        for line in snapshot.guidance:
            guidance.append(f"• {line}\n", style=theme.text)
        console.print(Panel(guidance, title="Coverage", border_style=theme.accent, padding=(1, 2)))

    def _exists(self, path: str) -> str:
        try:
            return "present" if Path(path).exists() else "missing"
        except PermissionError:
            return "inaccessible"
        except OSError:
            return "missing"

    def _is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
