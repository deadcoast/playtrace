from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from playtrace.store.db import Database


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
        db = Database(request.db_path)
        db.bootstrap()

        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO mappings (
                    mapping_id, target, title, classification, launcher,
                    ignore, created_at, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"mapping:{uuid4().hex}",
                    request.target,
                    request.title,
                    request.classification,
                    request.launcher,
                    1 if request.ignore else 0,
                    datetime.now().isoformat(),
                    "high",
                ),
            )
            conn.commit()
