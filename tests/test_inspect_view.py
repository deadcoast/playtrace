from __future__ import annotations

import json
from pathlib import Path

from playtrace.services.inspector import InspectRequest, InspectorService
from playtrace.store.db import Database


def test_inspect_view_shows_confidence_and_parent_chain(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    with db.connect() as conn:
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
                "title:elden_ring",
                "ELDEN RING",
                "game",
                "high",
                "high",
                "Steam",
                600,
                0,
                0,
                "exact",
                1,
                0,
                0,
                "high",
                None,
                None,
                json.dumps(["security_log"]),
                json.dumps([]),
                json.dumps([]),
            ),
        )
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, title_id, exe_id, user_sid, started_at, ended_at,
                duration_seconds, foreground_seconds, bytes_in, bytes_out,
                confidence, evidence_sources, evidence_ids, parent_chain, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session:1",
                "title:elden_ring",
                "path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe",
                "S-1-5-21-demo",
                "2026-04-11T18:42:03+00:00",
                "2026-04-11T18:52:03+00:00",
                600,
                0,
                0,
                0,
                "exact",
                json.dumps(["security_log"]),
                json.dumps(["evidence:start", "evidence:end"]),
                json.dumps(["steam.exe"]),
                json.dumps([]),
            ),
        )
        conn.execute(
            """
            INSERT INTO mappings (
                mapping_id, target, title, classification, launcher,
                ignore, created_at, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mapping:1",
                "path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe",
                "ELDEN RING",
                "game",
                "Steam",
                0,
                "2026-04-11T18:00:00+00:00",
                "high",
            ),
        )
        conn.commit()

    detail = InspectorService().load(
        InspectRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            target="ELDEN RING",
        )
    )

    assert detail.title == "ELDEN RING"
    assert detail.runtime_confidence == "exact"
    assert detail.parent_chains == [["steam.exe"]]
    assert detail.evidence_sources == ["security_log"]
    assert detail.evidence_source_counts == {"security_log": 1}
    assert detail.evidence_ids == ["evidence:end", "evidence:start"]
    assert detail.mapping_source == "manual"
    assert any("exact runtime" in line.lower() for line in detail.confidence_reasoning)
    assert any("manual mapping" in line.lower() for line in detail.confidence_reasoning)


def test_inspect_view_accepts_raw_executable_paths(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    with db.connect() as conn:
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
                "title:balatro",
                "Balatro",
                "game",
                "high",
                "high",
                "Steam",
                600,
                0,
                0,
                "exact",
                1,
                0,
                0,
                "high",
                None,
                None,
                json.dumps(["security_log"]),
                json.dumps([]),
                json.dumps([]),
            ),
        )
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, title_id, exe_id, user_sid, started_at, ended_at,
                duration_seconds, foreground_seconds, bytes_in, bytes_out,
                confidence, evidence_sources, evidence_ids, parent_chain, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session:2",
                "title:balatro",
                "path:d:\\games\\balatro\\balatro.exe",
                "S-1-5-21-demo",
                "2026-04-11T18:42:03+00:00",
                "2026-04-11T18:52:03+00:00",
                600,
                0,
                0,
                0,
                "exact",
                json.dumps(["security_log"]),
                json.dumps(["evidence:balatro:start", "evidence:balatro:end"]),
                json.dumps([]),
                json.dumps([]),
            ),
        )
        conn.commit()

    detail = InspectorService().load(
        InspectRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            target=r"D:\Games\Balatro\balatro.exe",
        )
    )

    assert detail.title == "Balatro"
    assert detail.runtime_confidence == "exact"
