from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.db import Database
from playtrace.store.repositories import (
    ExecutableRepository,
    MappingRepository,
    SessionRepository,
    TitleRepository,
)


def _mapping_strategy() -> st.SearchStrategy[UserMapping]:
    component = st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz0123456789_-")),
        min_size=1,
        max_size=12,
    )
    path = st.builds(
        lambda drive, part1, part2, exe_name: rf"{drive}:\{part1}\{part2}\{exe_name}.exe",
        st.characters(min_codepoint=97, max_codepoint=122),
        component,
        component,
        component,
    )
    title = st.text(
        alphabet=st.sampled_from(list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ")),
        min_size=1,
        max_size=24,
    ).filter(lambda value: value.strip() != "")
    launcher = st.none() | title

    return st.builds(
        lambda identifier, target, mapping_title, classification, mapping_launcher, ignore: UserMapping(
            mapping_id=f"mapping:{identifier}",
            target=target,
            title=mapping_title,
            classification=classification,
            launcher=mapping_launcher,
            ignore=ignore,
            created_at=datetime(2026, 4, 14, 18, 0, 0, tzinfo=timezone.utc),
        ),
        st.text(
            alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz0123456789")),
            min_size=1,
            max_size=12,
        ),
        path,
        title,
        st.none() | st.sampled_from(list(Classification)),
        launcher,
        st.booleans(),
    )


def test_mapping_repository_find_by_id_returns_none_for_missing_entity(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))

    assert repository.find_by_id("mapping:missing") is None


def test_mapping_repository_find_all_returns_empty_list_for_empty_table(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))

    assert repository.find_all() == []


def test_mapping_repository_find_all_returns_saved_entities(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))
    first = _mapping(mapping_id="mapping:1", target=r"path:d:\games\balatro\balatro.exe", title="Balatro")
    second = _mapping(mapping_id="mapping:2", target=r"path:d:\games\hades\hades.exe", title="Hades")

    repository.save(first)
    repository.save(second)

    assert repository.find_all() == [
        replace(first, normalized_key=first.target),
        replace(second, normalized_key=second.target),
    ]


@given(_mapping_strategy())
def test_mapping_repository_save_returns_typed_entity_with_normalized_key(
    mapping: UserMapping,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / "save.db")
        db.bootstrap()
        repository = MappingRepository(db)

        saved = repository.save(mapping)

        assert isinstance(saved, UserMapping)
        assert saved.mapping_id == mapping.mapping_id
        assert saved.target.startswith("path:")
        assert saved.normalized_key == saved.target
        assert saved.title == mapping.title


@given(_mapping_strategy())
def test_mapping_repository_converts_rows_to_dataclasses(
    mapping: UserMapping,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / "rows.db")
        db.bootstrap()

        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO mappings (
                    mapping_id, target, title, classification, launcher,
                    ignore, created_at, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping.mapping_id,
                    mapping.target,
                    mapping.title,
                    mapping.classification.value if mapping.classification else None,
                    mapping.launcher,
                    1 if mapping.ignore else 0,
                    mapping.created_at.isoformat(),
                    mapping.confidence.value,
                ),
            )
            conn.commit()

        loaded = MappingRepository(db).find_by_id(mapping.mapping_id)

        assert isinstance(loaded, UserMapping)
        assert loaded is not None
        assert loaded.mapping_id == mapping.mapping_id
        assert loaded.title == mapping.title
        assert loaded.classification == mapping.classification
        assert loaded.ignore == mapping.ignore
        assert loaded.created_at == mapping.created_at
        assert loaded.normalized_key == _normalized_target(mapping.target)


def test_mapping_repository_save_updates_existing_entity(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))
    original = _mapping(mapping_id="mapping:update", target=r"path:d:\games\balatro\balatro.exe", title="Balatro")
    repository.save(original)

    updated = repository.save(
        replace(
            original,
            title="Balatro Deluxe",
            classification=Classification.HELPER,
            launcher="Steam",
            ignore=True,
        )
    )

    assert updated == replace(
        original,
        title="Balatro Deluxe",
        classification=Classification.HELPER,
        launcher="Steam",
        ignore=True,
        normalized_key=original.target,
    )


def test_mapping_repository_delete_removes_entity_and_missing_delete_is_noop(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))
    repository.save(_mapping(mapping_id="mapping:delete", target=r"path:d:\games\balatro\balatro.exe"))

    repository.delete("mapping:delete")
    repository.delete("mapping:missing")

    assert repository.find_by_id("mapping:delete") is None


def test_executable_repository_round_trips_persisted_fields_and_finds_by_normalized_key(
    tmp_path: Path,
) -> None:
    db = _bootstrap_db(tmp_path)
    repository = ExecutableRepository(db)
    executable = _executable()

    saved = repository.save(executable)
    loaded = repository.find_by_normalized_key(executable.normalized_key)

    assert saved == executable
    assert loaded == executable


def test_session_repository_round_trips_and_finds_by_exe_id(tmp_path: Path) -> None:
    db = _bootstrap_db(tmp_path)
    _seed_executable(db, _executable())
    repository = SessionRepository(db)
    session = _session()

    saved = repository.save(session)

    assert saved == session
    assert repository.find_by_id(session.session_id) == session
    assert repository.find_by_exe_id(session.exe_id) == [session]


def test_title_repository_round_trips_relation_fields_and_finds_by_classification(
    tmp_path: Path,
) -> None:
    db = _bootstrap_db(tmp_path)
    executable = _executable()
    _seed_executable(db, executable)
    repository = TitleRepository(db)
    title = _title(executable.exe_id)

    saved = repository.save(title)
    loaded = repository.find_by_classification(Classification.GAME)

    assert saved == title
    assert repository.find_by_id(title.title_id) == title
    assert loaded == [title]


def test_title_repository_update_replaces_title_executable_links(tmp_path: Path) -> None:
    db = _bootstrap_db(tmp_path)
    first_executable = _executable()
    second_executable = replace(
        first_executable,
        exe_id="sha1:0123456789abcdef0123456789abcdef01234567",
        normalized_key="sha1:0123456789abcdef0123456789abcdef01234567",
        path=None,
        filename="eldenring-helper.exe",
        original_filename="eldenring-helper.exe",
        sha1="0123456789abcdef0123456789abcdef01234567",
    )
    _seed_executable(db, first_executable)
    _seed_executable(db, second_executable)
    repository = TitleRepository(db)

    repository.save(_title(first_executable.exe_id))
    updated = repository.save(
        replace(
            _title(first_executable.exe_id),
            executable_ids=[second_executable.exe_id],
        )
    )

    assert updated.executable_ids == [second_executable.exe_id]

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT exe_id FROM title_executables WHERE title_id = ? ORDER BY exe_id ASC",
            ("title:elden_ring",),
        ).fetchall()

    assert [row["exe_id"] for row in rows] == [second_executable.exe_id]


def test_mapping_repository_find_by_target_normalizes_raw_windows_paths(tmp_path: Path) -> None:
    repository = MappingRepository(_bootstrap_db(tmp_path))
    saved = repository.save(
        _mapping(
            mapping_id="mapping:lookup",
            target=r"D:\Games\Balatro\balatro.exe",
            title="Balatro",
        )
    )

    loaded = repository.find_by_target(r'd:\games\BALATRO\balatro.exe')

    assert loaded == saved


def test_repository_uses_database_connection_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = _bootstrap_db(tmp_path)
    repository = MappingRepository(db)
    calls: list[str] = []
    original_connect = db.connect

    def tracking_connect() -> sqlite3.Connection:
        calls.append("connect")
        return original_connect()

    monkeypatch.setattr(db, "connect", tracking_connect)

    repository.find_all()
    repository.save(_mapping(mapping_id="mapping:tracked", target=r"path:d:\games\balatro\balatro.exe"))
    repository.find_by_id("mapping:tracked")
    repository.delete("mapping:tracked")

    assert len(calls) >= 4


def _bootstrap_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    return db


def _mapping(
    *,
    mapping_id: str = "mapping:1",
    target: str = r"path:d:\games\balatro\balatro.exe",
    title: str = "Balatro",
    classification: Classification | None = Classification.GAME,
    launcher: str | None = None,
    ignore: bool = False,
    created_at: datetime = datetime(2026, 4, 14, 18, 0, 0, tzinfo=timezone.utc),
) -> UserMapping:
    return UserMapping(
        mapping_id=mapping_id,
        target=target,
        title=title,
        classification=classification,
        launcher=launcher,
        ignore=ignore,
        created_at=created_at,
    )


def _executable() -> ExecutableIdentity:
    return ExecutableIdentity(
        exe_id="path:d:\\games\\elden ring\\game\\eldenring.exe",
        normalized_key="path:d:\\games\\elden ring\\game\\eldenring.exe",
        path=r"d:\games\elden ring\game\eldenring.exe",
        filename="eldenring.exe",
        original_filename="eldenring.exe",
        product_name="ELDEN RING",
        file_description="ELDEN RING",
        signer="FromSoftware",
        company_name="FromSoftware",
        sha1="abcdef0123456789abcdef0123456789abcdef01",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        ignored=False,
        first_seen=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 12, 18, 0, 0, tzinfo=timezone.utc),
    )


def _session() -> SessionRecord:
    return SessionRecord(
        session_id="session:1",
        title_id="title:elden_ring",
        exe_id="path:d:\\games\\elden ring\\game\\eldenring.exe",
        user_sid="S-1-5-21-demo",
        started_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 11, 19, 0, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        foreground_seconds=2400,
        bytes_in=1024,
        bytes_out=2048,
        confidence=RuntimeConfidence.EXACT,
        evidence_sources=["security_log", "prefetch"],
        evidence_ids=["evidence:start", "evidence:end"],
        parent_chain=["steam.exe"],
        notes=["merged from process start and exit evidence"],
    )


def _title(exe_id: str) -> TitleAggregate:
    return TitleAggregate(
        title_id="title:elden_ring",
        title="Elden Ring",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        runtime=RuntimeStats(
            confirmed_seconds=7200,
            estimated_seconds=0,
            foreground_seconds=5400,
            confidence=ConfidenceLevel.HIGH,
        ),
        launches=LaunchStats(
            confirmed=2,
            inferred=0,
            gui=1,
            confidence=ConfidenceLevel.HIGH,
        ),
        first_seen=datetime(2026, 4, 1, 18, 0, 0, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 14, 18, 0, 0, tzinfo=timezone.utc),
        executable_ids=[exe_id],
        evidence_sources=["security_log", "prefetch"],
        tags=["soulslike"],
        notes=["manual mapping applied"],
    )


def _seed_executable(db: Database, executable: ExecutableIdentity) -> None:
    ExecutableRepository(db).save(executable)


def _normalized_target(target: str) -> str | None:
    return IdentityNormalizer().normalize_executable_target(target)
