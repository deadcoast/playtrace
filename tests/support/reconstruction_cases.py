from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import (
    ConfidenceLevel,
    EvidenceStrength,
    EvidenceType,
    RuntimeConfidence,
    SourceName,
)
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class ReconstructionCase:
    executables: list[ExecutableIdentity]
    sessions: list[SessionRecord]
    evidence: list[EvidenceRecord]


def duplicate_title_case() -> ReconstructionCase:
    primary = _executable(
        exe_id="path:d:\\games\\elden ring\\eldenring.exe",
        path=r"D:\Games\ELDEN RING\eldenring.exe",
        filename="eldenring.exe",
        product_name="ELDEN RING",
    )
    related = _executable(
        exe_id="path:d:\\games\\eldenring\\eldenring_dx12.exe",
        path=r"D:\Games\eldenring\eldenring_dx12.exe",
        filename="eldenring_dx12.exe",
        product_name="eldenring",
    )
    sessions = [
        _session(primary.exe_id, 3600),
        _session(related.exe_id, 1200),
    ]
    return ReconstructionCase(
        executables=[primary, related],
        sessions=sessions,
        evidence=[],
    )


def weak_title_case() -> ReconstructionCase:
    unknown = ExecutableIdentity(
        exe_id="path:d:\\games\\mystery\\bootstrap.exe",
        normalized_key="path:d:\\games\\mystery\\bootstrap.exe",
        path=r"D:\Games\Mystery\bootstrap.exe",
        filename="bootstrap.exe",
        original_filename=None,
        product_name=None,
        file_description=None,
        signer=None,
        company_name=None,
        sha1=None,
        classification_confidence=ConfidenceLevel.UNKNOWN,
    )
    return ReconstructionCase(
        executables=[unknown],
        sessions=[],
        evidence=[],
    )


def split_session_case() -> ReconstructionCase:
    started_at = datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc)
    exe_path = r"D:\Games\Balatro\balatro.exe"
    evidence = [
        _evidence(
            "evidence:start:1",
            EvidenceType.PROCESS_START,
            started_at,
            {
                "pid": 100,
                "parent_pid": 90,
                "exe_path": exe_path,
                "user_sid": "S-1-5-21-demo",
            },
        ),
        _evidence(
            "evidence:end:1",
            EvidenceType.PROCESS_EXIT,
            started_at.replace(minute=5),
            {
                "pid": 100,
                "parent_pid": 90,
                "exe_path": exe_path,
                "user_sid": "S-1-5-21-demo",
            },
        ),
        _evidence(
            "evidence:start:2",
            EvidenceType.PROCESS_START,
            started_at.replace(minute=5, second=5),
            {
                "pid": 101,
                "parent_pid": 90,
                "exe_path": exe_path,
                "user_sid": "S-1-5-21-demo",
            },
        ),
        _evidence(
            "evidence:end:2",
            EvidenceType.PROCESS_EXIT,
            started_at.replace(minute=20),
            {
                "pid": 101,
                "parent_pid": 90,
                "exe_path": exe_path,
                "user_sid": "S-1-5-21-demo",
            },
        ),
    ]
    return ReconstructionCase(
        executables=[],
        sessions=[],
        evidence=evidence,
    )


def _executable(
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


def _session(exe_id: str, duration_seconds: int) -> SessionRecord:
    started_at = datetime(2026, 4, 18, 18, 0, 0, tzinfo=timezone.utc)
    return SessionRecord(
        session_id=f"session:{exe_id}",
        title_id=None,
        exe_id=exe_id,
        user_sid="S-1-5-21-demo",
        started_at=started_at,
        ended_at=started_at,
        duration_seconds=duration_seconds,
        confidence=RuntimeConfidence.EXACT,
        evidence_sources=["security_log"],
    )


def _evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    observed_at: datetime,
    value: dict[str, object],
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        artifact_id=f"artifact:{evidence_id}",
        source=SourceName.SECURITY_LOG,
        evidence_type=evidence_type,
        observed_at=observed_at,
        strength=EvidenceStrength.EXACT,
        value=value,
    )
