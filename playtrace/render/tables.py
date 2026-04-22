from __future__ import annotations

from datetime import datetime

from rich.table import Table

from playtrace.models.enums import ConfidenceLevel
from playtrace.models.session import SessionRecord
from playtrace.models.report import DuplicateCandidate
from playtrace.models.title import TitleAggregate
from playtrace.render.badges import confidence_badge

MISSING_LABEL = "-"
UNKNOWN_LABEL = "UNKNOWN"


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(seconds, 0), 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes:02d}m"


def format_runtime(seconds: int, confidence: ConfidenceLevel) -> str:
    if seconds <= 0 and confidence is ConfidenceLevel.UNKNOWN:
        return UNKNOWN_LABEL
    return format_duration(seconds)


def titles_table(titles: list[TitleAggregate]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Title", ratio=3, overflow="fold")
    table.add_column("Runtime", justify="right", min_width=len("Runtime"), no_wrap=True, overflow="fold")
    table.add_column("Launches", justify="right", min_width=len("Launches"), no_wrap=True, overflow="fold")
    table.add_column("Confidence", min_width=len("Confidence"), no_wrap=True, overflow="fold")
    table.add_column("Launcher", ratio=2, overflow="fold")

    for title in titles:
        total_runtime = title.runtime.confirmed_seconds + title.runtime.estimated_seconds
        launches = title.launches.confirmed + title.launches.inferred + title.launches.gui
        table.add_row(
            title.title,
            format_runtime(total_runtime, title.runtime.confidence),
            str(launches),
            confidence_badge(title.runtime.confidence.value),
            title.launcher or MISSING_LABEL,
        )

    return table


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return MISSING_LABEL
    return value.strftime("%Y-%m-%d %H:%M")


def format_session_runtime(session: SessionRecord) -> str:
    if session.duration_seconds is None:
        return UNKNOWN_LABEL
    return format_duration(session.duration_seconds)


def sessions_table(rows: list[tuple[str, SessionRecord]]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Title", ratio=3, overflow="fold")
    table.add_column("Started", min_width=len("Started"), overflow="fold")
    table.add_column("Ended", min_width=len("Ended"), overflow="fold")
    table.add_column("Runtime", justify="right", min_width=len("Runtime"), no_wrap=True, overflow="fold")
    table.add_column("Confidence", min_width=len("Confidence"), no_wrap=True, overflow="fold")
    table.add_column("User", ratio=2, overflow="fold")

    for title, session in rows:
        table.add_row(
            title,
            format_timestamp(session.started_at),
            format_timestamp(session.ended_at),
            format_session_runtime(session),
            session.confidence.value.upper(),
            session.user_sid or MISSING_LABEL,
        )

    return table


def duplicate_candidates_table(candidates: list[DuplicateCandidate]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Primary", ratio=2, overflow="fold")
    table.add_column("Related", ratio=3, overflow="fold")
    table.add_column("Reason", ratio=2, overflow="fold")

    for candidate in candidates:
        table.add_row(
            candidate.primary_title,
            ", ".join(candidate.related_titles),
            "; ".join(candidate.reasons) or MISSING_LABEL,
        )

    return table
