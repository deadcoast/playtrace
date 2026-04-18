from __future__ import annotations

from datetime import datetime, timezone

from playtrace.merge.sessions import SessionMerger
from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import (
    EvidenceStrength,
    EvidenceType,
    RuntimeConfidence,
    SourceName,
)
from tests.support.reconstruction_cases import split_session_case


def test_session_merger_pairs_4688_and_4689_by_pid() -> None:
    start = EvidenceRecord(
        evidence_id="evidence:start",
        artifact_id="artifact:start",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 15320,
            "parent_pid": 9012,
            "exe_path": r'D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe',
            "user_sid": "S-1-5-21-demo",
        },
    )
    end = EvidenceRecord(
        evidence_id="evidence:end",
        artifact_id="artifact:end",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_EXIT,
        observed_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 15320,
            "parent_pid": 9012,
            "exe_path": r'd:\steamlibrary\steamapps\common\elden ring\game\ELDENRING.EXE',
            "user_sid": "S-1-5-21-demo",
        },
    )

    sessions = SessionMerger().build_sessions([end, start])

    assert len(sessions) == 1
    session = sessions[0]
    assert session.started_at == start.observed_at
    assert session.ended_at == end.observed_at
    assert session.duration_seconds == 600
    assert session.confidence == RuntimeConfidence.EXACT
    assert session.evidence_sources == ["security_log"]
    assert session.evidence_ids == ["evidence:start", "evidence:end"]


def test_session_merger_coerces_naive_timestamps_to_utc() -> None:
    start = EvidenceRecord(
        evidence_id="evidence:start",
        artifact_id="artifact:start",
        source=SourceName.AMCACHE,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 3),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 15320,
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )
    end = EvidenceRecord(
        evidence_id="evidence:end",
        artifact_id="artifact:end",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_EXIT,
        observed_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 15320,
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )

    sessions = SessionMerger().build_sessions([end, start])

    assert len(sessions) == 1
    assert sessions[0].started_at == datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc)
    assert sessions[0].ended_at == end.observed_at
    assert sessions[0].duration_seconds == 600


def test_session_merger_treats_unparseable_pid_as_none() -> None:
    start = EvidenceRecord(
        evidence_id="evidence:start",
        artifact_id="artifact:start",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": "not-a-number",
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )
    end = EvidenceRecord(
        evidence_id="evidence:end",
        artifact_id="artifact:end",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_EXIT,
        observed_at=datetime(2026, 4, 11, 18, 52, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "pid": "not-a-number",
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )

    sessions = SessionMerger().build_sessions([end, start])

    assert len(sessions) == 1
    assert ":session:unknown:" in sessions[0].session_id
    assert sessions[0].session_id.endswith(":evidence:start")


def test_session_merger_uses_evidence_id_when_timestamp_missing() -> None:
    start_a = EvidenceRecord(
        evidence_id="evidence:start:a",
        artifact_id="artifact:start:a",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=None,
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 42,
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )
    start_b = EvidenceRecord(
        evidence_id="evidence:start:b",
        artifact_id="artifact:start:b",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=None,
        strength=EvidenceStrength.EXACT,
        value={
            "pid": 42,
            "exe_path": r"D:\Games\Balatro\balatro.exe",
            "user_sid": "S-1-5-21-demo",
        },
    )

    sessions = SessionMerger().build_sessions([start_a, start_b])

    assert len(sessions) == 2
    assert {session.session_id for session in sessions} == {
        "path:d:\\games\\balatro\\balatro.exe:session:42:none:evidence:start:a",
        "path:d:\\games\\balatro\\balatro.exe:session:42:none:evidence:start:b",
    }


def test_session_merger_keeps_launcher_child_continuity_in_one_session() -> None:
    case = split_session_case()

    sessions = SessionMerger().build_sessions(case.evidence)

    assert len(sessions) == 1
    assert sessions[0].confidence is RuntimeConfidence.EXACT
