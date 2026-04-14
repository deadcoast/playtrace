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
