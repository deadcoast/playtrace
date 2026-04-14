from __future__ import annotations

import json
import socket
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.report import CoverageSummary, ReportSnapshot
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.store.schema import SCHEMA_SQL


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def bootstrap(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def count_sessions(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])

    def count_titles(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0])

    def replace_sessions_from_scan(self, sessions: list[SessionRecord], source: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE instr(evidence_sources, ?) > 0",
                (source,),
            )
            conn.executemany(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, title_id, exe_id, user_sid, started_at, ended_at,
                    duration_seconds, foreground_seconds, bytes_in, bytes_out,
                    confidence, evidence_sources, parent_chain, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session.session_id,
                        session.title_id,
                        session.exe_id,
                        session.user_sid,
                        session.started_at.isoformat() if session.started_at else None,
                        session.ended_at.isoformat() if session.ended_at else None,
                        session.duration_seconds,
                        session.foreground_seconds,
                        session.bytes_in,
                        session.bytes_out,
                        session.confidence.value,
                        json.dumps(session.evidence_sources),
                        json.dumps(session.parent_chain),
                        json.dumps(session.notes),
                    )
                    for session in sessions
                ],
            )
            conn.commit()

    def rebuild_titles_from_sessions(self) -> None:
        with self.connect() as conn:
            session_rows = conn.execute("SELECT * FROM sessions").fetchall()
            conn.execute("DELETE FROM titles")

            grouped: dict[str, list[sqlite3.Row]] = {}
            for row in session_rows:
                title_id = row["title_id"] or self._title_id_from_exe(row["exe_id"])
                grouped.setdefault(title_id, []).append(row)

            for title_id, rows in grouped.items():
                title = self._title_from_title_id(title_id)
                launch_count = len(rows)
                confirmed_seconds = sum(int(row["duration_seconds"] or 0) for row in rows)
                foreground_seconds = sum(int(row["foreground_seconds"] or 0) for row in rows)
                first_seen = min((row["started_at"] for row in rows if row["started_at"]), default=None)
                last_seen = max((row["ended_at"] or row["started_at"] for row in rows if row["started_at"]), default=None)
                evidence = sorted({src for row in rows for src in json.loads(row["evidence_sources"])})
                launchers = Counter(self._infer_launcher(row["exe_id"]) for row in rows)
                launcher = None
                if launchers:
                    launcher = max(launchers, key=launchers.get)
                    if launcher == "Unknown":
                        launcher = None

                classification = self._classify_title(title, rows[0]["exe_id"])
                runtime_conf = "high" if confirmed_seconds > 0 else "unknown"
                conn.execute(
                    """
                    INSERT INTO titles (
                        title_id, title, classification, classification_confidence, title_confidence,
                        launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                        runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                        launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title_id,
                        title,
                        classification,
                        "medium",
                        "medium",
                        launcher,
                        confirmed_seconds,
                        0,
                        foreground_seconds,
                        runtime_conf,
                        launch_count,
                        0,
                        0,
                        "high",
                        first_seen,
                        last_seen,
                        json.dumps(evidence),
                        json.dumps([]),
                        json.dumps([]),
                    ),
                )
            conn.commit()

    def load_snapshot(self, limit: int) -> ReportSnapshot:
        with self.connect() as conn:
            title_rows = conn.execute(
                """
                SELECT *
                FROM titles
                ORDER BY (confirmed_seconds + estimated_seconds) DESC, title ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            total_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS tracked_titles,
                    COALESCE(SUM(confirmed_seconds), 0) AS confirmed_runtime_seconds,
                    COALESCE(SUM(estimated_seconds), 0) AS estimated_runtime_seconds,
                    COALESCE(SUM(launches_confirmed), 0) AS confirmed_sessions
                FROM titles
                """
            ).fetchone()
            session_rows = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY COALESCE(ended_at, started_at) DESC
                LIMIT 5
                """
            ).fetchall()

        titles: list[TitleAggregate] = []
        for row in title_rows:
            titles.append(
                TitleAggregate(
                    title_id=row["title_id"],
                    title=row["title"],
                    classification=Classification(row["classification"]),
                    classification_confidence=ConfidenceLevel(row["classification_confidence"]),
                    title_confidence=ConfidenceLevel(row["title_confidence"]),
                    launcher=row["launcher"],
                    runtime=RuntimeStats(
                        confirmed_seconds=int(row["confirmed_seconds"]),
                        estimated_seconds=int(row["estimated_seconds"]),
                        foreground_seconds=int(row["foreground_seconds"]),
                        confidence=ConfidenceLevel(row["runtime_confidence"]),
                    ),
                    launches=LaunchStats(
                        confirmed=int(row["launches_confirmed"]),
                        inferred=int(row["launches_inferred"]),
                        gui=int(row["launches_gui"]),
                        confidence=ConfidenceLevel(row["launches_confidence"]),
                    ),
                    first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
                    last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
                    evidence_sources=json.loads(row["evidence_sources"]),
                    tags=json.loads(row["tags"]),
                    notes=json.loads(row["notes"]),
                )
            )

        sessions: list[SessionRecord] = []
        for row in session_rows:
            sessions.append(
                SessionRecord(
                    session_id=row["session_id"],
                    title_id=row["title_id"],
                    exe_id=row["exe_id"],
                    user_sid=row["user_sid"],
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                    duration_seconds=row["duration_seconds"],
                    foreground_seconds=int(row["foreground_seconds"] or 0),
                    bytes_in=int(row["bytes_in"] or 0),
                    bytes_out=int(row["bytes_out"] or 0),
                    confidence=ConfidenceLevel(row["confidence"]),
                    evidence_sources=json.loads(row["evidence_sources"]),
                    parent_chain=json.loads(row["parent_chain"]),
                    notes=json.loads(row["notes"]),
                )
            )

        warnings: list[str] = []
        if int(total_row["tracked_titles"] or 0) == 0:
            warnings.append("No titles found. Run `playtrace scan` to ingest Security log history.")
        else:
            warnings.append("This snapshot is built from exact Security log sessions only.")
            warnings.append("Launcher and helper suppression are still heuristic-first in this build.")

        return ReportSnapshot(
            generated_at=datetime.now(),
            host_name=socket.gethostname(),
            coverage=CoverageSummary(
                tracked_titles=int(total_row["tracked_titles"] or 0),
                confirmed_runtime_seconds=int(total_row["confirmed_runtime_seconds"] or 0),
                estimated_runtime_seconds=int(total_row["estimated_runtime_seconds"] or 0),
                confirmed_sessions=int(total_row["confirmed_sessions"] or 0),
                unmapped_executables=0,
            ),
            top_titles=titles,
            recent_sessions=sessions,
            warnings=warnings,
        )

    def _title_id_from_exe(self, exe_id: str) -> str:
        stem = Path(exe_id).stem or "unknown"
        normalized = "_".join(stem.lower().split())
        return f"title:{normalized}"

    def _title_from_title_id(self, title_id: str) -> str:
        slug = title_id.split(":", 1)[-1].replace("_", " ").strip()
        return " ".join(word.capitalize() for word in slug.split()) or "Unknown"

    def _infer_launcher(self, exe_id: str) -> str:
        value = exe_id.lower()
        if "steam" in value:
            return "Steam"
        if "epic" in value:
            return "Epic"
        if "gog" in value:
            return "GOG"
        if "battle.net" in value or "battlenet" in value:
            return "Battle.net"
        if "ea" in value:
            return "EA"
        return "Unknown"

    def _classify_title(self, title: str, exe_id: str) -> str:
        lower = f"{title} {exe_id}".lower()
        if any(token in lower for token in ["steam.exe", "epicgameslauncher", "galaxyclient", "eadesktop", "upc.exe"]):
            return "launcher"
        if any(token in lower for token in ["crash", "updater", "helper", "service", "bootstrap", "redist"]):
            return "helper"
        if exe_id.lower().startswith("c:\\windows\\"):
            return "system"
        return "game"
