from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playtrace.render.console import build_console
from playtrace.render.report_views import render_report
from playtrace.render.theme import get_theme
from playtrace.store.db import Database


@dataclass(slots=True)
class ReportRequest:
    db_path: Path
    config_path: Path | None
    theme: str
    density: str
    limit: int


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

    def render_default(self, request: ReportRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        snapshot = db.load_snapshot(limit=request.limit)

        console = build_console()
        theme = get_theme(request.theme)
        render_report(console, theme, snapshot)

    def render_titles(self, request: TitlesRequest) -> None:
        raise NotImplementedError

    def render_sessions(self, request: SessionsRequest) -> None:
        raise NotImplementedError
