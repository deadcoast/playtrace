from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from playtrace.models.enums import ConfidenceLevel
from playtrace.models.enums import Classification
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.services.mapper import MapRequest, MapperService
from playtrace.store.db import Database
from playtrace.utils.clock import Clock


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


def test_mapper_uses_clock_for_mapping_timestamps(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "playtrace.db"
    fixed = datetime(2026, 4, 12, 9, 30, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(Clock, "utc_now", staticmethod(lambda: fixed))

    MapperService().apply(
        MapRequest(
            db_path=db_path,
            target=r"D:\Games\Balatro\balatro.exe",
            title="Balatro",
            classification=Classification.GAME,
        )
    )

    mappings = Database(db_path).load_user_mappings()

    assert len(mappings) == 1
    assert mappings[0].created_at == fixed


def test_mapper_auto_merge_rolls_back_mapping_changes_when_merge_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "playtrace.db"
    _seed_duplicate_titles(
        db_path,
        primary=_title("title:elden-ring", "ELDEN RING", ConfidenceLevel.HIGH, 300),
        related=_title("title:eldenring", "eldenring", ConfidenceLevel.LOW, 600),
    )

    def fail_merge(self, *args, **kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(MapperService, "_merge_persisted_titles", fail_merge)

    with pytest.raises(RuntimeError, match="boom"):
        MapperService().apply_auto_merge(MapRequest(db_path=db_path, auto=True))

    mappings = Database(db_path).load_user_mappings()
    snapshot = Database(db_path).load_snapshot(limit=10)

    assert mappings == []
    assert snapshot.coverage.tracked_titles == 2


def test_mapper_auto_merge_prefers_higher_confidence_primary_title(tmp_path: Path) -> None:
    db_path = tmp_path / "playtrace.db"
    _seed_duplicate_titles(
        db_path,
        primary=_title("title:elden-ring", "ELDEN RING", ConfidenceLevel.HIGH, 300),
        related=_title("title:eldenring", "eldenring", ConfidenceLevel.LOW, 600),
    )

    merged = MapperService().apply_auto_merge(MapRequest(db_path=db_path, auto=True))

    snapshot = Database(db_path).load_snapshot(limit=10)

    assert merged == 1
    assert snapshot.coverage.tracked_titles == 1
    assert snapshot.top_titles[0].title_id == "title:elden-ring"
    assert snapshot.top_titles[0].title == "ELDEN RING"


def _seed_duplicate_titles(db_path: Path, *, primary: TitleAggregate, related: TitleAggregate) -> None:
    db = Database(db_path)
    db.bootstrap()
    db.replace_titles([primary, related])

    with db.connect() as conn:
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
            (related.title_id, "exe:eldenring-dx12"),
        )
        conn.commit()


def _title(
    title_id: str,
    title: str,
    confidence: ConfidenceLevel,
    confirmed_seconds: int,
) -> TitleAggregate:
    return TitleAggregate(
        title_id=title_id,
        title=title,
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=confidence,
        launcher="Steam",
        runtime=RuntimeStats(
            confirmed_seconds=confirmed_seconds,
            estimated_seconds=0,
            foreground_seconds=max(confirmed_seconds - 60, 0),
            confidence=ConfidenceLevel.HIGH,
        ),
        launches=LaunchStats(
            confirmed=1,
            inferred=0,
            gui=1,
            confidence=ConfidenceLevel.HIGH,
        ),
    )
