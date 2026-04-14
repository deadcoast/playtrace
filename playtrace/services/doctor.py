from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DoctorRequest:
    db_path: Path
    theme: str


class DoctorService:
    def render(self, request: DoctorRequest) -> None:
        raise NotImplementedError