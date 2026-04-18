from __future__ import annotations

import json
from pathlib import Path

from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
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


def test_inspect_view_uses_rebuilt_session_links(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()

    scan_run_id = db.create_scan_run(["security_log"])
    artifacts = [
        RawArtifact(
            artifact_id="artifact:start",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=None,
            raw_ref="security_log:4688:15320",
            payload={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
        RawArtifact(
            artifact_id="artifact:end",
            scan_run_id=scan_run_id,
            source=SourceName.SECURITY_LOG,
            observed_at=None,
            raw_ref="security_log:4689:15320",
            payload={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
    ]
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:start",
            artifact_id="artifact:start",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_START,
            observed_at=None,
            strength=EvidenceStrength.EXACT,
            value={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
        EvidenceRecord(
            evidence_id="evidence:end",
            artifact_id="artifact:end",
            source=SourceName.SECURITY_LOG,
            evidence_type=EvidenceType.PROCESS_EXIT,
            observed_at=None,
            strength=EvidenceStrength.EXACT,
            value={
                "pid": 15320,
                "parent_pid": 9012,
                "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                "user_sid": "S-1-5-21-demo",
            },
        ),
    ]

    db.replace_artifacts_for_scan(scan_run_id, artifacts)
    db.replace_evidence_for_scan(scan_run_id, evidence)

    with db.connect() as conn:
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
                "Elden Ring",
                "game",
                "Steam",
                0,
                "2026-04-11T18:00:00+00:00",
                "high",
            ),
        )
        conn.commit()

    db.rebuild_from_artifacts_and_mappings()

    detail = InspectorService().load(
        InspectRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            target="Elden Ring",
        )
    )

    assert detail.title == "Elden Ring"
    assert detail.evidence_sources == ["security_log"]
    assert detail.evidence_ids == ["evidence:end", "evidence:start"]


def test_inspect_view_surfaces_alternate_titles_from_lineage(tmp_path: Path) -> None:
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

    detail = InspectorService().load(
        InspectRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            target="ELDEN RING",
        )
    )

    assert "eldenring" in detail.alternate_titles
    assert detail.confidence_reasoning


def test_inspect_view_uses_title_executable_evidence_when_sessions_are_missing(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "playtrace.db"
    db = Database(db_path)
    db.bootstrap()
    scan_run_id = db.create_scan_run(["userassist"])

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
                "title:steam",
                "Steam",
                "launcher",
                "high",
                "high",
                None,
                0,
                0,
                0,
                "unknown",
                0,
                0,
                0,
                "unknown",
                None,
                None,
                json.dumps(["userassist"]),
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
                r"path:c:\program files (x86)\steam\steam.exe",
                r"path:c:\program files (x86)\steam\steam.exe",
                r"C:\Program Files (x86)\Steam\steam.exe",
                "steam.exe",
                "steam.exe",
                None,
                None,
                None,
                None,
                None,
                "launcher",
                "high",
                0,
                None,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO title_executables (title_id, exe_id) VALUES (?, ?)",
            ("title:steam", r"path:c:\program files (x86)\steam\steam.exe"),
        )
        conn.execute(
            """
            INSERT INTO artifacts (
                artifact_id, scan_run_id, source, observed_at, raw_ref, payload
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "artifact:userassist:1",
                    scan_run_id,
                    "userassist",
                    "2026-04-16T08:40:52.798000+00:00",
                    r"userassist:C:\Program Files (x86)\Steam\steam.exe",
                    json.dumps({"entry": r"C:\Program Files (x86)\Steam\steam.exe"}),
                ),
        )
        conn.execute(
            """
            INSERT INTO evidence_links (
                evidence_id, scan_run_id, artifact_id, source, evidence_type,
                observed_at, strength, value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "evidence:userassist:1",
                    scan_run_id,
                    "artifact:userassist:1",
                    "userassist",
                "interactive_launch",
                "2026-04-16T08:40:52.798000+00:00",
                "interactive",
                json.dumps({"exe_path": r"C:\Program Files (x86)\Steam\steam.exe"}),
            ),
        )
        conn.commit()

    detail = InspectorService().load(
        InspectRequest(
            db_path=db_path,
            theme="mono",
            density="comfortable",
            target="Steam",
        )
    )

    assert detail.title == "Steam"
    assert detail.evidence_sources == ["userassist"]
    assert detail.evidence_source_counts == {"userassist": 1}
    assert detail.evidence_ids == ["evidence:userassist:1"]
