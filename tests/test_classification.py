from __future__ import annotations

from datetime import datetime, timezone

from playtrace.classify.rules import classify_executable
from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.evidence import RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName
from playtrace.parsers.amcache import AmCacheParser
from playtrace.parsers.prefetch import PrefetchParser
from playtrace.parsers.userassist import UserAssistParser


def test_prefetch_parser_emits_execution_count_evidence() -> None:
    artifact = RawArtifact(
        artifact_id="artifact:prefetch:1",
        scan_run_id="scan:test",
        source=SourceName.PREFETCH,
        observed_at=datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc),
        raw_ref="prefetch:ELDENRING.EXE-1A2B3C4D.pf",
        payload={
            "exe_name": "ELDENRING.EXE",
            "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
            "run_count": 34,
            "last_run_times": [
                "2026-04-11T18:42:05+00:00",
                "2026-04-10T20:11:07+00:00",
            ],
        },
    )

    records = PrefetchParser().parse([artifact])

    assert any(record.evidence_type == EvidenceType.EXECUTION_COUNT for record in records)
    assert any(record.evidence_type == EvidenceType.RECENT_EXECUTION for record in records)
    assert all(record.strength == EvidenceStrength.STRONG for record in records)


def test_userassist_parser_emits_interactive_launch_and_focus() -> None:
    artifact = RawArtifact(
        artifact_id="artifact:userassist:1",
        scan_run_id="scan:test",
        source=SourceName.USERASSIST,
        observed_at=datetime(2026, 4, 11, 18, 41, 50, tzinfo=timezone.utc),
        raw_ref="userassist:C:\\Program Files (x86)\\Steam\\steam.exe",
        payload={
            "entry": r"C:\Program Files (x86)\Steam\steam.exe",
            "run_count": 19,
            "focus_time_ms": 24034000,
            "last_run": "2026-04-11T18:41:50+00:00",
            "user_sid": "S-1-5-21-demo",
        },
    )

    records = UserAssistParser().parse([artifact])

    assert any(record.evidence_type == EvidenceType.INTERACTIVE_LAUNCH for record in records)
    assert any(record.evidence_type == EvidenceType.FOREGROUND_USAGE for record in records)
    assert all(record.strength == EvidenceStrength.INTERACTIVE for record in records)


def test_amcache_parser_emits_identity_evidence() -> None:
    artifact = RawArtifact(
        artifact_id="artifact:amcache:1",
        scan_run_id="scan:test",
        source=SourceName.AMCACHE,
        observed_at=datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc),
        raw_ref="amcache:D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
        payload={
            "exe_path": r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
            "sha1": "abc123",
            "product_name": "ELDEN RING",
            "company_name": "FromSoftware, Inc.",
            "file_description": "ELDEN RING",
            "original_filename": "eldenring.exe",
        },
    )

    records = AmCacheParser().parse([artifact])

    assert len(records) == 1
    assert records[0].evidence_type == EvidenceType.IDENTITY
    assert records[0].strength == EvidenceStrength.STRONG


def test_classify_executable_marks_windows_binaries_as_system() -> None:
    executable = ExecutableIdentity(
        exe_id="path:c:\\windows\\system32\\notepad.exe",
        normalized_key="path:c:\\windows\\system32\\notepad.exe",
        path=r"C:\Windows\System32\notepad.exe",
        filename="notepad.exe",
        original_filename="notepad.exe",
        product_name="Microsoft Windows",
        file_description="Notepad",
        signer=None,
        company_name=None,
        sha1=None,
    )

    classification, subtype, confidence = classify_executable(executable)

    assert classification == Classification.SYSTEM
    assert subtype is None
    assert confidence == ConfidenceLevel.HIGH


def test_classify_executable_leaves_weak_non_system_signals_unknown() -> None:
    executable = ExecutableIdentity(
        exe_id="path:c:\\users\\demo\\downloads\\chatgpt.exe",
        normalized_key="path:c:\\users\\demo\\downloads\\chatgpt.exe",
        path=r"C:\Users\demo\Downloads\chatgpt.exe",
        filename="chatgpt.exe",
        original_filename="chatgpt.exe",
        product_name="ChatGPT",
        file_description="ChatGPT",
        signer=None,
        company_name=None,
        sha1=None,
    )

    classification, subtype, confidence = classify_executable(executable)

    assert classification == Classification.UNKNOWN
    assert subtype is None
    assert confidence == ConfidenceLevel.UNKNOWN
