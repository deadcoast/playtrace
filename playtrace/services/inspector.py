from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class InspectRequest:
    db_path: Path
    theme: str
    density: str
    target: str


class InspectorService:
    def render(self, request: InspectRequest) -> None:
        raise NotImplementedError