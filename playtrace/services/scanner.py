from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScanRequest:
    db_path: Path
    config_path: Path | None
    sources: list[str]
    full: bool = False


class ScannerService:
    def run(self, request: ScanRequest) -> None:
        raise NotImplementedError