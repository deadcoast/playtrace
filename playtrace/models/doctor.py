from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DoctorFinding:
    severity: str
    code: str
    summary: str
    remediation: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DoctorSnapshot:
    environment_findings: list[DoctorFinding] = field(default_factory=list)
    data_findings: list[DoctorFinding] = field(default_factory=list)
