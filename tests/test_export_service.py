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
