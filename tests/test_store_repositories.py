from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.store.db import Database
from playtrace.store.repositories import (
    ExecutableRepository,
    MappingRepository,
    SessionRepository,
    TitleRepository,
)


def _build_database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    return db


def test_executable_repository_round_trips_entities(tmp_path: Path) -> None:
    db = _build_database(tmp_path)
    repo = ExecutableRepository(db)
    executable = ExecutableIdentity(
        exe_id="exe:eldenring",
        normalized_key=r"path:d:\games\eldenring.exe",
        path=r"d:\games\eldenring.exe",
        filename="eldenring.exe",
        original_filename="eldenring.exe",
        product_name="ELDEN RING",
        file_description="ELDEN RING",
        signer="FromSoftware",
        company_name="FromSoftware",
        sha1="abc123",
        canonical_path=r"d:\games\eldenring.exe",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        first_seen=datetime(2026, 4, 17, 19, 0, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 17, 20, 0, tzinfo=timezone.utc),
    )

    saved = repo.save(executable)

    assert saved == executable
    assert repo.find_by_id("exe:eldenring") == executable
    assert repo.find_by_normalized_key(r"path:d:\games\eldenring.exe") == executable


def test_session_repository_round_trips_entities(tmp_path: Path) -> None:
    db = _build_database(tmp_path)
    repo = SessionRepository(db)
    session = SessionRecord(
        session_id="session:1",
        title_id="title:elden_ring",
        exe_id="exe:eldenring",
        user_sid="S-1-5-21-demo",
        started_at=datetime(2026, 4, 17, 19, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 17, 20, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        foreground_seconds=3500,
        bytes_in=1024,
        bytes_out=2048,
        confidence=RuntimeConfidence.EXACT,
        evidence_sources=["security_log"],
        evidence_ids=["evidence:start", "evidence:end"],
        parent_chain=["steam.exe"],
        notes=["merged from exact evidence"],
    )

    saved = repo.save(session)

    assert saved == session
    assert repo.find_by_id("session:1") == session
    assert repo.find_by_exe_id("exe:eldenring") == [session]


def test_title_repository_round_trips_entities(tmp_path: Path) -> None:
    db = _build_database(tmp_path)
    ExecutableRepository(db).save(
        ExecutableIdentity(
            exe_id="exe:eldenring",
            normalized_key=r"path:d:\games\eldenring.exe",
            path=r"d:\games\eldenring.exe",
            filename="eldenring.exe",
            original_filename="eldenring.exe",
            product_name="ELDEN RING",
            file_description="ELDEN RING",
            signer="FromSoftware",
            company_name="FromSoftware",
            sha1="abc123",
            canonical_path=r"d:\games\eldenring.exe",
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
        )
    )
    repo = TitleRepository(db)
    title = TitleAggregate(
        title_id="title:elden_ring",
        title="Elden Ring",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        runtime=RuntimeStats(
            confirmed_seconds=3600,
            estimated_seconds=0,
            foreground_seconds=3500,
            confidence=ConfidenceLevel.HIGH,
        ),
        launches=LaunchStats(
            confirmed=1,
            inferred=0,
            gui=1,
            confidence=ConfidenceLevel.HIGH,
        ),
        first_seen=datetime(2026, 4, 17, 19, 0, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 17, 20, 0, tzinfo=timezone.utc),
        executable_ids=["exe:eldenring"],
        evidence_sources=["security_log"],
        tags=["soulslike"],
        notes=["manually mapped"],
    )

    saved = repo.save(title)

    assert saved == title
    assert repo.find_by_id("title:elden_ring") == title
    assert repo.find_by_classification(Classification.GAME) == [title]


def test_mapping_repository_round_trips_entities_and_normalizes_target(tmp_path: Path) -> None:
    db = _build_database(tmp_path)
    repo = MappingRepository(db)
    mapping = UserMapping(
        mapping_id="mapping:1",
        target=r"D:\Games\Balatro\balatro.exe",
        title="Balatro",
        classification=Classification.GAME,
        launcher="Steam",
        ignore=False,
        created_at=datetime(2026, 4, 17, 19, 0, tzinfo=timezone.utc),
        confidence=ConfidenceLevel.HIGH,
    )

    saved = repo.save(mapping)

    assert saved.normalized_key == r"path:d:\games\balatro\balatro.exe"
    assert repo.find_by_id("mapping:1") == saved
    assert repo.find_by_target(r"D:\Games\Balatro\balatro.exe") == saved
