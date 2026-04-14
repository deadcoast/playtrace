from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from playtrace.models.evidence import EvidenceRecord, RawArtifact


@dataclass(slots=True)
class CollectContext:
    scan_run_id: str
    host_name: str
    temp_dir: Path
    full_scan: bool = False


class RawCollector(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def collect(self, context: CollectContext) -> list[RawArtifact]: ...


class EvidenceParser(Protocol):
    name: str

    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]: ...
