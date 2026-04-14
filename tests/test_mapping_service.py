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
