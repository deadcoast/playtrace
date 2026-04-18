from __future__ import annotations

from pathlib import Path

from playtrace.models.lineage import EntityLineageSnapshot, SourcesLineageSnapshot


class LineageService:
    def load_entity(self, db_path: Path, target: str) -> EntityLineageSnapshot:
        return EntityLineageSnapshot(
            title=target,
            runtime_confidence="unknown",
        )

    def load_sources(self, db_path: Path, target: str) -> SourcesLineageSnapshot:
        return SourcesLineageSnapshot(target=target)
