from __future__ import annotations

from datetime import datetime, timezone

from playtrace.merge.titles import TitleAggregator
from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord


def test_launcher_child_rule_prefers_longest_lived_game_process() -> None:
    launcher = _exe(
        exe_id="path:c:\\program files (x86)\\steam\\steam.exe",
        path=r"C:\Program Files (x86)\Steam\steam.exe",
        filename="steam.exe",
        product_name="Steam",
    )
    game = _exe(
        exe_id="path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe",
        path=r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
        filename="eldenring.exe",
        product_name="ELDEN RING",
    )
    helper = _exe(
        exe_id="path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\start_protected_game.exe",
        path=r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\start_protected_game.exe",
        filename="start_protected_game.exe",
        product_name="Easy Anti-Cheat",
    )

    sessions = [
        _session(launcher.exe_id, 300, []),
        _session(game.exe_id, 7200, ["steam.exe"]),
        _session(helper.exe_id, 120, ["steam.exe"]),
    ]

    titles = TitleAggregator().build([launcher, game, helper], sessions)

    assert len(titles) == 1
    title = titles[0]
    assert title.title == "ELDEN RING"
    assert title.launcher == "Steam"
    assert game.exe_id in title.executable_ids
    assert launcher.exe_id not in title.executable_ids
    assert helper.exe_id not in title.executable_ids


def test_manual_mapping_overrides_metadata_fallback() -> None:
    executable = _exe(
        exe_id="soft:weird-launcher",
        path=r"D:\Games\weirdlauncher\gamebin\start.exe",
        filename="start.exe",
        product_name="Bootstrap",
    )
    mapping = UserMapping(
        mapping_id="mapping:1",
        target=executable.exe_id,
        title="My Game",
        classification=Classification.GAME,
        launcher="Custom",
        ignore=False,
        created_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
    )

    titles = TitleAggregator().build([executable], [_session(executable.exe_id, 1200, [])], [mapping])

    assert len(titles) == 1
    title = titles[0]
    assert title.title == "My Game"
    assert title.launcher == "Custom"
    assert title.title_confidence == ConfidenceLevel.HIGH


def test_helper_process_is_suppressed_from_primary_title() -> None:
    game = _exe(
        exe_id="path:d:\\games\\balatro\\balatro.exe",
        path=r"D:\Games\Balatro\balatro.exe",
        filename="balatro.exe",
        product_name="Balatro",
    )
    helper = _exe(
        exe_id="path:d:\\games\\balatro\\crashreporter.exe",
        path=r"D:\Games\Balatro\crashreporter.exe",
        filename="crashreporter.exe",
        product_name="Crash Reporter",
    )

    titles = TitleAggregator().build(
        [game, helper],
        [
            _session(game.exe_id, 1800, []),
            _session(helper.exe_id, 45, ["balatro.exe"]),
        ],
    )

    assert len(titles) == 1
    assert titles[0].title == "Balatro"
    assert titles[0].executable_ids == [game.exe_id]


def test_ignore_mapping_suppresses_executable() -> None:
    executable = _exe(
        exe_id="path:d:\\games\\ignored\\ignored.exe",
        path=r"D:\Games\Ignored\ignored.exe",
        filename="ignored.exe",
        product_name="Ignored Game",
    )
    mapping = UserMapping(
        mapping_id="mapping:ignore",
        target=executable.exe_id,
        title="Ignored Game",
        classification=Classification.GAME,
        launcher=None,
        ignore=True,
        created_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        normalized_key=executable.exe_id,
    )

    titles = TitleAggregator().build([executable], [_session(executable.exe_id, 1200, [])], [mapping])

    assert titles == []


def test_title_aggregator_emits_multiple_titles_for_independent_games() -> None:
    balatro = _exe(
        exe_id="path:d:\\games\\balatro\\balatro.exe",
        path=r"D:\Games\Balatro\balatro.exe",
        filename="balatro.exe",
        product_name="Balatro",
    )
    hades = _exe(
        exe_id="path:d:\\games\\hades\\hades.exe",
        path=r"D:\Games\Hades\hades.exe",
        filename="hades.exe",
        product_name="Hades",
    )

    titles = TitleAggregator().build(
        [balatro, hades],
        [
            _session(balatro.exe_id, 1800, []),
            _session(hades.exe_id, 2400, []),
        ],
    )

    assert {title.title for title in titles} == {"Balatro", "Hades"}
    assert {tuple(title.executable_ids) for title in titles} == {
        (balatro.exe_id,),
        (hades.exe_id,),
    }


def _exe(
    *,
    exe_id: str,
    path: str,
    filename: str,
    product_name: str,
) -> ExecutableIdentity:
    return ExecutableIdentity(
        exe_id=exe_id,
        normalized_key=exe_id,
        path=path,
        filename=filename,
        original_filename=filename,
        product_name=product_name,
        file_description=product_name,
        signer=None,
        company_name=None,
        sha1=None,
    )


def _session(exe_id: str, duration_seconds: int, parent_chain: list[str]) -> SessionRecord:
    return SessionRecord(
        session_id=f"session:{exe_id}",
        title_id=None,
        exe_id=exe_id,
        user_sid="S-1-5-21-demo",
        started_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        duration_seconds=duration_seconds,
        confidence=RuntimeConfidence.EXACT,
        evidence_sources=["security_log"],
        parent_chain=parent_chain,
    )
