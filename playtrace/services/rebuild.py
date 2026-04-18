from __future__ import annotations

from pathlib import Path

from playtrace.models.repair import RepairCounts, RepairPreview


class RebuildService:
    def plan(self, db_path: Path, settings=None) -> RepairPreview:
        return RepairPreview(counts=RepairCounts())

    def apply(self, db_path: Path, *, preview: RepairPreview, confirmed: bool) -> RepairPreview:
        if not confirmed:
            raise PermissionError("Repair apply requires --yes.")
        return preview
