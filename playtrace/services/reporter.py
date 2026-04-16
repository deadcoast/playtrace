from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path

from rich.panel import Panel
from rich.text import Text

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.render.console import build_console
from playtrace.render.report_views import render_report
from playtrace.render.tables import sessions_table, titles_table
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
        db = Database(request.db_path)
        db.bootstrap()
        titles = self._load_titles(db, request)

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
        sessions = self._load_sessions(db, request)

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

    def _load_titles(self, db: Database, request: TitlesRequest) -> list[TitleAggregate]:
        filters: list[str] = []
        params: list[object] = []
        if request.classification:
            filters.append("classification = ?")
            params.append(request.classification.lower())
        if request.launcher:
            filters.append("LOWER(COALESCE(launcher, '')) = ?")
            params.append(request.launcher.lower())

        order_by = {
            "runtime": "(confirmed_seconds + estimated_seconds) DESC, title ASC",
            "launches": "(launches_confirmed + launches_inferred) DESC, title ASC",
            "last_seen": "last_seen DESC, title ASC",
            "title": "title ASC",
        }.get(request.sort_by, "(confirmed_seconds + estimated_seconds) DESC, title ASC")

        query = "SELECT * FROM titles"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += f" ORDER BY {order_by} LIMIT ?"
        params.append(request.limit)

        with db.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [self._title_from_row(row) for row in rows]

    def _load_sessions(self, db: Database, request: SessionsRequest) -> list[tuple[str, SessionRecord]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.days)
        filters = ["COALESCE(sessions.ended_at, sessions.started_at) >= ?"]
        params: list[object] = [cutoff.isoformat()]
        if request.title:
            filters.append("LOWER(COALESCE(titles.title, sessions.title_id, sessions.exe_id)) LIKE ?")
            params.append(f"%{request.title.lower()}%")

        query = f"""
            SELECT
                sessions.*,
                titles.title AS resolved_title
            FROM sessions
            LEFT JOIN titles ON titles.title_id = sessions.title_id
            WHERE {' AND '.join(filters)}
            ORDER BY COALESCE(sessions.ended_at, sessions.started_at) DESC, sessions.session_id DESC
            LIMIT ?
        """
        params.append(request.limit)

        with db.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [
            (
                row["resolved_title"] or row["title_id"] or row["exe_id"],
                SessionRecord(
                    session_id=row["session_id"],
                    title_id=row["title_id"],
                    exe_id=row["exe_id"],
                    user_sid=row["user_sid"],
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                    duration_seconds=row["duration_seconds"],
                    foreground_seconds=int(row["foreground_seconds"]),
                    bytes_in=int(row["bytes_in"]),
                    bytes_out=int(row["bytes_out"]),
                    confidence=self._enum_value(RuntimeConfidence, row["confidence"], RuntimeConfidence.UNKNOWN),
                    evidence_sources=json.loads(row["evidence_sources"]),
                    evidence_ids=json.loads(row["evidence_ids"]),
                    parent_chain=json.loads(row["parent_chain"]),
                    notes=json.loads(row["notes"]),
                ),
            )
            for row in rows
        ]

    def _title_from_row(self, row) -> TitleAggregate:
        return TitleAggregate(
            title_id=row["title_id"],
            title=row["title"],
            classification=self._enum_value(Classification, row["classification"], Classification.UNKNOWN),
            classification_confidence=self._enum_value(
                ConfidenceLevel, row["classification_confidence"], ConfidenceLevel.UNKNOWN
            ),
            title_confidence=self._enum_value(ConfidenceLevel, row["title_confidence"], ConfidenceLevel.UNKNOWN),
            launcher=row["launcher"],
            runtime=RuntimeStats(
                confirmed_seconds=int(row["confirmed_seconds"]),
                estimated_seconds=int(row["estimated_seconds"]),
                foreground_seconds=int(row["foreground_seconds"]),
                confidence=self._enum_value(ConfidenceLevel, row["runtime_confidence"], ConfidenceLevel.UNKNOWN),
            ),
            launches=LaunchStats(
                confirmed=int(row["launches_confirmed"]),
                inferred=int(row["launches_inferred"]),
                gui=int(row["launches_gui"]),
                confidence=self._enum_value(ConfidenceLevel, row["launches_confidence"], ConfidenceLevel.UNKNOWN),
            ),
            first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
            evidence_sources=json.loads(row["evidence_sources"]),
            tags=json.loads(row["tags"]),
            notes=json.loads(row["notes"]),
        )

    def _enum_value(self, enum_type: type[Enum], value: str | None, default):
        if not value:
            return default
        try:
            return enum_type(value)
        except ValueError:
            return default
