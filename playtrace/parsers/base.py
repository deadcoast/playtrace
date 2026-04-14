from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from playtrace.models.artifacts import ArtifactRecord


@dataclass(slots=True)
class ParseContext:
    host_name: str
    temp_dir: Path
    full_scan: bool = False


class ArtifactParser(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def parse(self, context: ParseContext) -> list[ArtifactRecord]: ...