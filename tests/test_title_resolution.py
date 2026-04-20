from __future__ import annotations

from datetime import datetime, timezone

from playtrace.classify.heuristics import choose_primary_executable
from playtrace.classify.resolver import ResolvedTitle, TitleResolver
from playtrace.merge.titles import TitleAggregator
from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import Classification, ConfidenceLevel, RuntimeConfidence
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from tests.support.reconstruction_cases import (
    duplicate_title_case,
    duplicate_title_case_with_remaining_ambiguity,
    weak_title_case,
)


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


def test_title_resolution_emits_duplicate_candidates_for_similar_executables() -> None:
    case = duplicate_title_case_with_remaining_ambiguity()

    result = TitleResolver().resolve(
        case.executables,
        case.sessions,
        mappings=[],
    )

    assert result.duplicate_candidates


def test_title_resolution_applies_config_classification_overrides_below_user_mappings() -> None:
    executable = _exe(
        exe_id="path:d:\\games\\custom\\game.exe",
        path=r"D:\Games\Custom\game.exe",
        filename="game.exe",
        product_name="Bootstrap",
    )
    mapping = UserMapping(
        mapping_id="mapping:1",
        target=executable.exe_id,
        title="Mapped Game",
        classification=None,
        launcher="Custom",
        ignore=False,
        created_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        normalized_key=executable.exe_id,
    )

    result = TitleResolver().resolve(
        [executable],
        [_session(executable.exe_id, 1200, [])],
        mappings=[mapping],
        config_overrides={r"D:\Games\Custom\game.exe": "game"},
    )

    assert len(result.titles) == 1
    assert result.titles[0].title == "Mapped Game"
    assert result.titles[0].classification is Classification.GAME


def test_duplicate_candidates_prefer_higher_confidence_titles() -> None:
    medium = ResolvedTitle(
        title_id="title:elden-ring",
        title="ELDEN RING",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher="Steam",
        primary_exe_id="exe:1",
    )
    low = ResolvedTitle(
        title_id="title:eldenring",
        title="eldenring",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.LOW,
        launcher="Steam",
        primary_exe_id="exe:2",
    )

    candidates = TitleResolver()._duplicate_candidates([low, medium])

    assert len(candidates) == 1
    assert candidates[0].primary_title_id == "title:elden-ring"
    assert candidates[0].primary_title == "ELDEN RING"


def test_duplicate_candidates_require_more_than_shared_launcher() -> None:
    left = ResolvedTitle(
        title_id="title:alpha-protocol",
        title="Alpha Protocol",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:alpha",
    )
    right = ResolvedTitle(
        title_id="title:balatro",
        title="Balatro",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:beta",
    )

    assert TitleResolver()._duplicate_candidates([left, right]) == []


def test_duplicate_candidates_keep_reconstructed_variants() -> None:
    left = ResolvedTitle(
        title_id="title:elden-ring",
        title="ELDEN RING",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:1",
    )
    right = ResolvedTitle(
        title_id="title:elden-ring-deluxe",
        title="Elden Ring Deluxe",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher="Steam",
        primary_exe_id="exe:2",
    )

    candidates = TitleResolver()._duplicate_candidates([left, right])

    assert len(candidates) == 1
    assert candidates[0].primary_title == "ELDEN RING"


def test_duplicate_candidates_keep_fuzzy_variants_without_shared_tokens() -> None:
    left = ResolvedTitle(
        title_id="title:balatro",
        title="Balatro",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher=None,
        primary_exe_id="exe:1",
    )
    right = ResolvedTitle(
        title_id="title:balatroo",
        title="Balatroo",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher=None,
        primary_exe_id="exe:2",
    )

    candidates = TitleResolver()._duplicate_candidates([left, right])

    assert len(candidates) == 1
    assert candidates[0].primary_title == "Balatro"


def test_duplicate_candidates_keep_non_ascii_near_matches() -> None:
    left = ResolvedTitle(
        title_id="title:pokemon",
        title="Pokemon",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher=None,
        primary_exe_id="exe:1",
    )
    right = ResolvedTitle(
        title_id="title:pokemon-accented",
        title="Pokémon",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher=None,
        primary_exe_id="exe:2",
    )

    candidates = TitleResolver()._duplicate_candidates([left, right])

    assert len(candidates) == 1
    assert candidates[0].primary_title == "Pokemon"


class CountingTitleResolver(TitleResolver):
    def __init__(self) -> None:
        super().__init__()
        self.duplicate_reason_calls = 0

    def _duplicate_reasons(self, left: ResolvedTitle, right: ResolvedTitle) -> list[str]:
        self.duplicate_reason_calls += 1
        return super()._duplicate_reasons(left, right)


def test_duplicate_candidates_reduce_verification_fanout_for_unrelated_titles() -> None:
    titles = [
        ResolvedTitle(
            title_id=f"title:{index}",
            title=f"{index:02x}{(index * 37) % 256:02x}{(index * 91) % 256:02x}",
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH,
            launcher=None,
            primary_exe_id=f"exe:{index}",
        )
        for index in range(40)
    ]
    resolver = CountingTitleResolver()

    candidates = resolver._duplicate_candidates(titles)

    assert candidates == []
    assert resolver.duplicate_reason_calls < 100


def test_duplicate_candidates_reduce_verification_fanout_for_titles_sharing_only_single_digit_tokens() -> None:
    titles = [
        ResolvedTitle(
            title_id=f"title:series:{index}",
            title=f"{index:02x}{(index * 37) % 256:02x}{(index * 91) % 256:02x} 2",
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH,
            launcher=None,
            primary_exe_id=f"exe:{index}",
        )
        for index in range(40)
    ]
    resolver = CountingTitleResolver()

    candidates = resolver._duplicate_candidates(titles)

    assert candidates == []
    assert resolver.duplicate_reason_calls < 100


def test_duplicate_candidates_reduce_fanout_for_dense_common_token_buckets() -> None:
    titles = [
        ResolvedTitle(
            title_id=f"title:quest:{index}",
            title=(
                f"{chr(97 + (index % 20)) * 6}{chr(97 + (index // 20)) * 6} "
                f"quest "
                f"{chr(122 - (index % 20)) * 6}{chr(122 - (index // 20)) * 6}"
            ),
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH,
            launcher=None,
            primary_exe_id=f"exe:{index}",
        )
        for index in range(40)
    ]
    resolver = CountingTitleResolver()

    candidates = resolver._duplicate_candidates(titles)

    assert candidates == []
    assert resolver.duplicate_reason_calls < 100


def test_duplicate_candidates_only_include_titles_directly_verified_with_primary() -> None:
    primary = ResolvedTitle(
        title_id="title:mystery-quest",
        title="Mystery Quest",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher=None,
        primary_exe_id="exe:1",
    )
    bridge = ResolvedTitle(
        title_id="title:mystery-quest-hd",
        title="Mystery Quest HD",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher=None,
        primary_exe_id="exe:2",
    )
    transitive = ResolvedTitle(
        title_id="title:quest-hd",
        title="Quest HD",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.LOW,
        launcher=None,
        primary_exe_id="exe:3",
    )

    candidates = TitleResolver()._duplicate_candidates([primary, bridge, transitive])

    assert len(candidates) == 1
    assert candidates[0].primary_title == "Mystery Quest"
    assert candidates[0].related_titles == ["Mystery Quest HD"]


def test_choose_primary_executable_returns_candidate_when_all_scores_are_negative() -> None:
    launcher = _exe(
        exe_id="path:c:\\program files (x86)\\steam\\steam.exe",
        path=r"C:\Program Files (x86)\Steam\steam.exe",
        filename="steam.exe",
        product_name="Steam",
    )
    helper = _exe(
        exe_id="path:c:\\games\\elden ring\\support\\helper.exe",
        path=r"C:\Games\ELDEN RING\Support\helper.exe",
        filename="helper.exe",
        product_name="Helper",
    )
    launcher.classification = Classification.LAUNCHER
    helper.classification = Classification.HELPER

    primary = choose_primary_executable([launcher, helper], [])

    assert primary is launcher


def test_title_aggregator_uses_non_session_evidence_for_launches_and_sources() -> None:
    executable = _exe(
        exe_id="path:c:\\program files (x86)\\battle.net\\battle.net launcher.exe",
        path="C:\\Program Files (x86)\\Battle.net\\Battle.net Launcher.exe",
        filename="Battle.net Launcher.exe",
        product_name="Battle.net Launcher",
    )
    evidence = [
        EvidenceRecord(
            evidence_id="evidence:userassist:launch:1",
            artifact_id="artifact:userassist:1",
            source=SourceName.USERASSIST,
            evidence_type=EvidenceType.INTERACTIVE_LAUNCH,
            observed_at=datetime(2026, 4, 16, 8, 40, 52, 798000, tzinfo=timezone.utc),
            strength=EvidenceStrength.INTERACTIVE,
            value={"exe_path": executable.path, "run_count": 1},
        ),
        EvidenceRecord(
            evidence_id="evidence:userassist:focus:1",
            artifact_id="artifact:userassist:1",
            source=SourceName.USERASSIST,
            evidence_type=EvidenceType.FOREGROUND_USAGE,
            observed_at=datetime(2026, 4, 16, 8, 40, 52, 798000, tzinfo=timezone.utc),
            strength=EvidenceStrength.INTERACTIVE,
            value={"exe_path": executable.path, "focus_time_ms": 24034000},
        ),
    ]

    titles = TitleAggregator().build([executable], [], evidence_records=evidence)

    assert len(titles) == 1
    title = titles[0]
    assert title.title == "Battle.net Launcher"
    assert title.launches.gui == 1
    assert title.launches.confidence is ConfidenceLevel.HIGH
    assert title.runtime.foreground_seconds == 24034
    assert title.evidence_sources == ["userassist"]
    assert title.first_seen == datetime(2026, 4, 16, 8, 40, 52, 798000, tzinfo=timezone.utc)
    assert title.last_seen == datetime(2026, 4, 16, 8, 40, 52, 798000, tzinfo=timezone.utc)


def test_title_resolver_prefers_evidence_backed_game_binary_over_launcher_labels() -> None:
    case = duplicate_title_case()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert [title.title for title in result.titles] == ["ELDEN RING"]
    assert result.duplicate_candidates == []


def test_title_resolver_preserves_ambiguity_when_evidence_is_too_weak() -> None:
    case = weak_title_case()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert result.titles[0].title_confidence is ConfidenceLevel.UNKNOWN
    assert "ambiguous" in " ".join(getattr(result.titles[0], "notes", [])).lower()


def test_duplicate_candidates_include_lineage_reasoning() -> None:
    case = duplicate_title_case_with_remaining_ambiguity()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert result.duplicate_candidates[0].reasons
    assert "metadata" in " ".join(result.duplicate_candidates[0].reasons).lower()


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
