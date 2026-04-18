from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawReportInput, RawSessionsInput, RawTitlesInput, UNSET
from playtrace.render.console import build_console
from playtrace.render.report_views import render_report, render_sessions_view, render_titles_view
from playtrace.render.theme import get_theme
from playtrace.models.report import ReportSnapshot
from playtrace.store.db import Database


@dataclass(slots=True, init=False)
class ReportRequest:
    db_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawReportInput
    show_duplicates: bool = False

    def __init__(
        self,
        *,
        db_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawReportInput | None = None,
        theme: str | None = None,
        density: str | None = None,
        limit: int | None = None,
        show_duplicates: bool = False,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawReportInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
            limit=limit if limit is not None else UNSET,
        )
        self.show_duplicates = show_duplicates


@dataclass(slots=True, init=False)
class TitlesRequest:
    db_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawTitlesInput

    def __init__(
        self,
        *,
        db_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawTitlesInput | None = None,
        theme: str | None = None,
        density: str | None = None,
        sort_by: str | None = None,
        classification: str | None = None,
        launcher: str | None = None,
        limit: int | None = None,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawTitlesInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
            sort_by=sort_by if sort_by is not None else UNSET,
            classification=classification if classification is not None else UNSET,
            launcher=launcher if launcher is not None else UNSET,
            limit=limit if limit is not None else UNSET,
        )


@dataclass(slots=True, init=False)
class SessionsRequest:
    db_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawSessionsInput

    def __init__(
        self,
        *,
        db_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawSessionsInput | None = None,
        theme: str | None = None,
        density: str | None = None,
        title: str | None = None,
        days: int | None = None,
        limit: int | None = None,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawSessionsInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
            title=title if title is not None else UNSET,
            days=days if days is not None else UNSET,
            limit=limit if limit is not None else UNSET,
        )


class ReporterService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()

    def build_report_snapshot(self, request: ReportRequest) -> ReportSnapshot:
        resolved = self._resolve_report(request)
        db = Database(request.db_path)
        db.bootstrap()
        snapshot = db.load_snapshot(limit=resolved.limit)
        if request.show_duplicates:
            snapshot.duplicate_candidates = db.load_duplicate_candidates()
        return snapshot

    def render_default(self, request: ReportRequest) -> None:
        resolved = self._resolve_report(request)
        snapshot = self.build_report_snapshot(request)
        console = build_console()
        theme = get_theme(resolved.presentation.theme)
        render_report(console, theme, snapshot)

    def render_titles(self, request: TitlesRequest) -> None:
        resolved = self._resolve_titles(request)
        db = Database(request.db_path)
        db.bootstrap()
        titles = db.load_titles(
            sort_by=resolved.sort_by or "runtime",
            classification=resolved.classification,
            launcher=resolved.launcher,
            limit=resolved.limit or 50,
        )

        console = build_console()
        theme = get_theme(resolved.presentation.theme)
        render_titles_view(
            console,
            theme,
            titles=titles,
            sort_by=resolved.sort_by or "runtime",
            classification=resolved.classification,
            launcher=resolved.launcher,
        )

    def render_sessions(self, request: SessionsRequest) -> None:
        resolved = self._resolve_sessions(request)
        db = Database(request.db_path)
        db.bootstrap()
        sessions = db.load_sessions(
            title=resolved.title,
            days=resolved.days or 30,
            limit=resolved.limit or 100,
        )

        console = build_console()
        theme = get_theme(resolved.presentation.theme)
        render_sessions_view(
            console,
            theme,
            sessions=sessions,
            days=resolved.days or 30,
            title_filter=resolved.title,
        )

    def _resolve_report(self, request: ReportRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_report(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )

    def _resolve_titles(self, request: TitlesRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_titles(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )

    def _resolve_sessions(self, request: SessionsRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_sessions(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )
