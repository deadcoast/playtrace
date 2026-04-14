from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExportRequest:
    db_path: Path
    output_path: Path
    format: str


class ExporterService:
    def run(self, request: ExportRequest) -> None:
        raise NotImplementedError