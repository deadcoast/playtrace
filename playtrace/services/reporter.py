from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.panel import Panel
from rich.text import Text

from playtrace.render.console import build_console
from playtrace.render.report_views import render_report
from playtrace.render.tables import sessions_table, titles_table
from playtrace.render.theme import get_theme
from playtrace.models.report import ReportSnapshot
from playtrace.store.db import Database


@dataclass(slots=True)
class ReportRequest:
    db_path: Path
    config_path: Path | None
    theme: str
    density: str
    limit: int
    show_duplicates: bool = False


@dataclass(slots=True)
class TitlesRequest:
    db_path: Path
    theme: str
    density: str
    sort_by: str
    classification: str | None
    launcher: str | None
    limit: int


@dataclass(slots=True)
class SessionsRequest:
    db_path: Path
    theme: str
    density: str
    title: str | None
    days: int
    limit: int


class ReporterService:
    def build_report_snapshot(self, request: ReportRequest) -> ReportSnapshot:
        db = Database(request.db_path)
        db.bootstrap()
        snapshot = db.load_snapshot(limit=request.limit)
        if request.show_duplicates:
            snapshot.duplicate_candidates = db.load_duplicate_candidates()
        return snapshot

    def render_default(self, request: ReportRequest) -> None:
        snapshot = self.build_report_snapshot(request)
        console = build_console()
        theme = get_theme(request.theme)
        render_report(console, theme, snapshot)

    def render_titles(self, request: TitlesRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        titles = db.load_titles(
            sort_by=request.sort_by,
            classification=request.classification,
            launcher=request.launcher,
            limit=request.limit,
        )

        console = build_console()
        theme = get_theme(request.theme)
        header = Text()
        header.append("playtrace TITLES\n", style=f"bold {theme.accent}")
        header.append(
            f"Sort: {request.sort_by}    Classification: {request.classification or 'all'}    "
            f"Launcher: {request.launcher or 'all'}",
            style=theme.dim,
        )
        console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))
        console.print(titles_table(titles))
        if not titles:
            console.print(Text("No titles matched the current filters.", style=theme.dim))

    def render_sessions(self, request: SessionsRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        sessions = db.load_sessions(
            title=request.title,
            days=request.days,
            limit=request.limit,
        )

        console = build_console()
        theme = get_theme(request.theme)
        header = Text()
        header.append("playtrace SESSIONS\n", style=f"bold {theme.accent}")
        header.append(
            f"Days: {request.days}    Title filter: {request.title or 'all'}",
            style=theme.dim,
        )
        console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))
        console.print(sessions_table(sessions))
        if not sessions:
            console.print(Text("No sessions matched the current filters.", style=theme.dim))
