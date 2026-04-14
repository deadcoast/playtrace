from __future__ import annotations

import json
import socket
import sqlite3
from datetime import datetime, timedelta
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

    def seed_demo_data(self) -> None:
        with self.connect() as conn:
            title_count = conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
            if title_count:
                return

            now = datetime.now()
            rows = [
                (
                    "title:elden_ring",
                    "Elden Ring",
                    "game",
                    "high",
                    "high",
                    "Steam",
                    152280,
                    0,
                    40020,
                    "high",
                    27,
                    7,
                    19,
                    "high",
                    (now - timedelta(days=120)).isoformat(),
                    (now - timedelta(days=3)).isoformat(),
                    json.dumps(["security_log", "prefetch", "userassist", "srum"]),
                    json.dumps(["soulslike"]),
                    json.dumps([]),
                ),
                (
                    "title:hades",
                    "Hades",
                    "game",
                    "high",
                    "high",
                    "Steam",
                    111900,
                    0,
                    28000,
                    "high",
                    44,
                    0,
                    31,
                    "high",
                    (now - timedelta(days=240)).isoformat(),
                    (now - timedelta(days=10)).isoformat(),
                    json.dumps(["prefetch", "userassist"]),
                    json.dumps(["roguelike"]),
                    json.dumps([]),
                ),
                (
                    "title:balatro",
                    "Balatro",
                    "game",
                    "medium",
                    "medium",
                    "Steam",
                    0,
                    65460,
                    9000,
                    "medium",
                    0,
                    63,
                    18,
                    "medium",
                    (now - timedelta(days=60)).isoformat(),
                    (now - timedelta(days=1)).isoformat(),
                    json.dumps(["prefetch", "userassist", "srum"]),
                    json.dumps(["deckbuilder"]),
                    json.dumps([]),
                ),
            ]
            conn.executemany(
                """
                INSERT INTO titles (
                    title_id, title, classification, classification_confidence, title_confidence,
                    launcher, confirmed_seconds, estimated_seconds, foreground_seconds,
                    runtime_confidence, launches_confirmed, launches_inferred, launches_gui,
                    launches_confidence, first_seen, last_seen, evidence_sources, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
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

        titles: list[TitleAggregate] = []
        confirmed_runtime = 0
        estimated_runtime = 0
        confirmed_sessions = 0

        for row in title_rows:
            confirmed_runtime += int(row["confirmed_seconds"])
            estimated_runtime += int(row["estimated_seconds"])
            confirmed_sessions += int(row["launches_confirmed"])
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

        return ReportSnapshot(
            generated_at=datetime.now(),
            host_name=socket.gethostname(),
            coverage=CoverageSummary(
                tracked_titles=len(titles),
                confirmed_runtime_seconds=confirmed_runtime,
                estimated_runtime_seconds=estimated_runtime,
                confirmed_sessions=confirmed_sessions,
                unmapped_executables=4,
            ),
            top_titles=titles,
            recent_sessions=[],
            warnings=[
                "This MVP report uses seeded demo rows until scan/ingest is implemented.",
                "Doctor only checks environment readiness, not artifact correctness.",
            ],
        )
