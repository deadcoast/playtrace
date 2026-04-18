from __future__ import annotations

import json
from pathlib import Path

from playtrace.services.lineage import LineageService
from playtrace.store.db import Database


def test_lineage_service_returns_canonical_title_with_alternate_labels(tmp_path: Path) -> None:
    db = _seed_entity_lineage_database(tmp_path)

    snapshot = LineageService().load_entity(db.path, target="ELDEN RING")

    assert snapshot.title == "ELDEN RING"
    assert "eldenring" in snapshot.alternate_titles
    assert snapshot.confidence_reasons


def test_lineage_service_surfaces_source_conflicts(tmp_path: Path) -> None:
    db = _seed_source_conflict_database(tmp_path)

    snapshot = LineageService().load_sources(
        db.path,
        target=r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe",
    )

    assert snapshot.conflicts


def test_lineage_service_prefers_high_confidence_title_when_multiple_titles_match_target(
    tmp_path: Path,
) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    target = "path:d:\\games\\elden ring\\eldenring.exe"

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
                "title:elden_ring_beta",
                "ELDEN RING Beta",
                "game",
                "medium",
                "low",
                "Steam",
                0,
                0,
                0,
                "estimated",
                0,
                1,
                0,
                "medium",
                None,
                None,
                json.dumps(["prefetch"]),
                json.dumps([]),
                json.dumps([]),
            ),
        )
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
                7200,
                0,
                0,
                "exact",
                3,
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
            INSERT INTO executables (
                exe_id, normalized_key, path, filename, original_filename, product_name,
                file_description, signer, company_name, sha1, classification,
                classification_confidence, ignored, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target,
                target,
                r"D:\Games\ELDEN RING\eldenring.exe",
                "eldenring.exe",
                "eldenring.exe",
                "ELDEN RING",
                "ELDEN RING",
                None,
                None,
                None,
                "game",
                "high",
                0,
                None,
                None,
            ),
        )
        conn.execute("INSERT INTO title_executables (title_id, exe_id) VALUES (?, ?)", ("title:elden_ring_beta", target))
        conn.execute("INSERT INTO title_executables (title_id, exe_id) VALUES (?, ?)", ("title:elden_ring", target))
        conn.commit()

    snapshot = LineageService().load_entity(db.path, target=target)

    assert snapshot.title == "ELDEN RING"


def _seed_entity_lineage_database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "playtrace.db")
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
                json.dumps(["security_log", "prefetch"]),
                json.dumps([]),
                json.dumps([]),
            ),
        )
        conn.execute(
            """
            INSERT INTO executables (
                exe_id, normalized_key, path, filename, original_filename, product_name,
                file_description, signer, company_name, sha1, classification,
                classification_confidence, ignored, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "path:d:\\games\\elden ring\\eldenring.exe",
                "path:d:\\games\\elden ring\\eldenring.exe",
                r"D:\Games\ELDEN RING\eldenring.exe",
                "eldenring.exe",
                "eldenring.exe",
                "ELDEN RING",
                "ELDEN RING",
                None,
                None,
                None,
                "game",
                "high",
                0,
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO executables (
                exe_id, normalized_key, path, filename, original_filename, product_name,
                file_description, signer, company_name, sha1, classification,
                classification_confidence, ignored, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "path:d:\\games\\eldenring\\eldenring_dx12.exe",
                "path:d:\\games\\eldenring\\eldenring_dx12.exe",
                r"D:\Games\eldenring\eldenring_dx12.exe",
                "eldenring_dx12.exe",
                "eldenring_dx12.exe",
                "eldenring",
                "eldenring",
                None,
                None,
                None,
                "game",
                "medium",
                0,
                None,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO title_executables (title_id, exe_id) VALUES (?, ?)",
            ("title:elden_ring", "path:d:\\games\\elden ring\\eldenring.exe"),
        )
        conn.execute(
            "INSERT INTO title_executables (title_id, exe_id) VALUES (?, ?)",
            ("title:elden_ring", "path:d:\\games\\eldenring\\eldenring_dx12.exe"),
        )
        conn.commit()

    return db


def _seed_source_conflict_database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    scan_run_id = db.create_scan_run(["security_log", "userassist"])
    target = r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO artifacts (artifact_id, scan_run_id, source, observed_at, raw_ref, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "artifact:security",
                scan_run_id,
                "security_log",
                "2026-04-18T18:00:00+00:00",
                "security_log:4688:200",
                json.dumps({"exe_path": target}),
            ),
        )
        conn.execute(
            """
            INSERT INTO artifacts (artifact_id, scan_run_id, source, observed_at, raw_ref, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "artifact:userassist",
                scan_run_id,
                "userassist",
                "2026-04-18T18:00:10+00:00",
                "userassist:battlenet",
                json.dumps({"exe_path": target}),
            ),
        )
        conn.execute(
            """
            INSERT INTO evidence_links (
                evidence_id, scan_run_id, artifact_id, source, evidence_type, observed_at, strength, value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evidence:security",
                scan_run_id,
                "artifact:security",
                "security_log",
                "process_start",
                "2026-04-18T18:00:00+00:00",
                "exact",
                json.dumps({"exe_path": target, "title_hint": "Battle.net Launcher"}),
            ),
        )
        conn.execute(
            """
            INSERT INTO evidence_links (
                evidence_id, scan_run_id, artifact_id, source, evidence_type, observed_at, strength, value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evidence:userassist",
                scan_run_id,
                "artifact:userassist",
                "userassist",
                "interactive_launch",
                "2026-04-18T18:00:10+00:00",
                "interactive",
                json.dumps({"exe_path": target, "title_hint": "Battle.net"}),
            ),
        )
        conn.commit()

    return db
