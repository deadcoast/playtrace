from __future__ import annotations

import json
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.title import TitleAggregate
from playtrace.services.exporter import ExportRequest, ExporterService
from playtrace.store.db import Database


def test_export_service_writes_snapshot_driven_json(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "out.json"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            TitleAggregate(
                title_id="title:balatro",
                title="Balatro",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher="Steam",
            )
        ]
    )

    ExporterService().run(
        ExportRequest(
            db_path=db_path,
            output_path=output_path,
            format="json",
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert payload["coverage"]["tracked_titles"] == 1


def test_export_service_includes_gui_launch_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "out.json"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            TitleAggregate(
                title_id="title:balatro",
                title="Balatro",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher="Steam",
            )
        ]
    )
    with db.connect() as conn:
        conn.execute(
            "UPDATE titles SET launches_gui = ? WHERE title_id = ?",
            (2, "title:balatro"),
        )
        conn.commit()

    ExporterService().run(
        ExportRequest(
            db_path=db_path,
            output_path=output_path,
            format="json",
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["titles"][0]["launches_gui"] == 2


def test_export_service_reuses_loaded_snapshot_for_json(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "out.json"
    db = Database(db_path)
    db.bootstrap()

    original_load_snapshot = Database.load_snapshot
    load_snapshot_calls = 0

    def spy_load_snapshot(self, limit: int):
        nonlocal load_snapshot_calls
        load_snapshot_calls += 1
        return original_load_snapshot(self, limit)

    monkeypatch.setattr(Database, "load_snapshot", spy_load_snapshot)

    ExporterService().run(
        ExportRequest(
            db_path=db_path,
            output_path=output_path,
            format="json",
        )
    )

    assert output_path.exists()
    assert load_snapshot_calls == 1


def test_export_service_writes_lineage_scope_json(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "lineage.json"
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
            ("title:elden_ring", "path:d:\\games\\eldenring\\eldenring_dx12.exe"),
        )
        conn.commit()

    ExporterService().run(
        ExportRequest(
            db_path=db_path,
            output_path=output_path,
            format="json",
            scope="lineage",
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["scope"] == "lineage"
    assert payload["entities"][0]["title"] == "ELDEN RING"
    assert "alternate_titles" in payload["entities"][0]
    assert "contributions" in payload["entities"][0]


def test_export_service_writes_repair_preview_scope_json(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    output_path = tmp_path / "repair.json"
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles(
        [
            TitleAggregate(
                title_id="title:balatro",
                title="Balatro",
                classification=Classification.GAME,
                classification_confidence=ConfidenceLevel.HIGH,
                title_confidence=ConfidenceLevel.HIGH,
                launcher="Steam",
            )
        ]
    )

    ExporterService().run(
        ExportRequest(
            db_path=db_path,
            output_path=output_path,
            format="json",
            scope="repair-preview",
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["scope"] == "repair-preview"
    assert payload["repair"]["counts"]["changed_titles"] >= 1
