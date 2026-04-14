from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from playtrace.models.enums import Classification
from playtrace.normalize.identity import IdentityNormalizer
from playtrace.store.db import Database


@dataclass(slots=True)
class MapRequest:
    db_path: Path
    target: str
    title: str
    classification: Classification | None
    launcher: str | None
    ignore: bool


class MapperService:
    def apply(self, request: MapRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        normalizer = IdentityNormalizer()
        normalized_target = normalizer.normalize_executable_target(request.target)
        stored_target = normalized_target or request.target.strip()

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
                    stored_target,
                    request.title,
                    request.classification.value if request.classification else None,
                    request.launcher,
                    1 if request.ignore else 0,
                    datetime.now(timezone.utc).isoformat(),
                    "high",
                ),
            )
            conn.commit()
