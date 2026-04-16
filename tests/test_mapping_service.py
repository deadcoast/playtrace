from __future__ import annotations

from pathlib import Path

from playtrace.models.enums import Classification
from playtrace.services.mapper import MapRequest, MapperService
from playtrace.store.db import Database


def test_mapper_normalizes_raw_path_targets(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"

    MapperService().apply(
        MapRequest(
            db_path=db_path,
            target=r"D:\Games\Balatro\balatro.exe",
            title="Balatro",
            classification=Classification.GAME,
            launcher="Steam",
            ignore=False,
        )
    )

    mappings = Database(db_path).load_user_mappings()

    assert len(mappings) == 1
    assert mappings[0].target == "path:d:\\games\\balatro\\balatro.exe"
    assert mappings[0].normalized_key == "path:d:\\games\\balatro\\balatro.exe"


def test_mapper_auto_merge_rebuilds_titles_after_applying_heuristics(tmp_path: Path) -> None:
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
                "title:elden-ring",
                "ELDEN RING",
                "game",
                "high",
                "high",
                "Steam",
                600,
                0,
                540,
                "high",
                1,
                0,
                1,
                "high",
                None,
                None,
                "[]",
                "[]",
                "[]",
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
                "title:eldenring",
                "eldenring",
                "game",
                "high",
                "high",
                "Steam",
                300,
                0,
                240,
                "high",
                1,
                0,
                1,
                "high",
                None,
                None,
                "[]",
                "[]",
                "[]",
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
                "exe:eldenring-dx12",
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
                "high",
                0,
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO title_executables (title_id, exe_id)
            VALUES (?, ?)
            """,
            ("title:eldenring", "exe:eldenring-dx12"),
        )
        conn.commit()

    merged = MapperService().apply_auto_merge(MapRequest(db_path=db_path, auto=True))
    rebuilt = Database(db_path).load_snapshot(limit=10)

    assert merged == 1
    assert rebuilt.coverage.tracked_titles == 1
