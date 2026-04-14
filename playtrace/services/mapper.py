from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MapRequest:
    db_path: Path
    target: str
    title: str
    classification: str | None
    launcher: str | None
    ignore: bool


class MapperService:
    def apply(self, request: MapRequest) -> None:
        raise NotImplementedError