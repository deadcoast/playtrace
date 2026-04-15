from __future__ import annotations

from datetime import datetime, timezone

from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.normalize.identity import IdentityNormalizer


def test_identity_normalizer_merges_case_only_path_variants() -> None:
    normalizer = IdentityNormalizer()
    first = EvidenceRecord(
        evidence_id="evidence:start:1",
        artifact_id="artifact:1",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "exe_path": r'D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe',
            "command_line": r'"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe"',
        },
    )
    second = EvidenceRecord(
        evidence_id="evidence:start:2",
        artifact_id="artifact:2",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "exe_path": r'd:\steamlibrary\steamapps\common\elden ring\game\ELDENRING.EXE',
            "command_line": r'"d:\steamlibrary\steamapps\common\elden ring\game\ELDENRING.EXE"',
        },
    )

    assert normalizer.build_key(first) == normalizer.build_key(second)
    assert normalizer.build_key(first).startswith("path:d:\\steamlibrary\\steamapps\\common\\elden ring\\game\\eldenring.exe")


def test_identity_normalizer_expands_environment_variables_via_path_normalizer(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    normalizer = IdentityNormalizer()
    record = EvidenceRecord(
        evidence_id="evidence:env",
        artifact_id="artifact:env",
        source=SourceName.SECURITY_LOG,
        evidence_type=EvidenceType.PROCESS_START,
        observed_at=datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc),
        strength=EvidenceStrength.EXACT,
        value={
            "exe_path": r"%ProgramFiles%/Steam/steam.exe",
        },
    )

    assert normalizer.canonical_path(record) == r"c:\program files\steam\steam.exe"
    assert normalizer.build_key(record) == r"path:c:\program files\steam\steam.exe"
    assert (
        normalizer.normalize_executable_target(r"path:%ProgramFiles%/Steam/steam.exe")
        == r"path:c:\program files\steam\steam.exe"
    )
