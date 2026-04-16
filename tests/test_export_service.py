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
