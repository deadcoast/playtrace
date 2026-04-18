from __future__ import annotations

from pathlib import Path

from playtrace.config.runtime import ReconstructionSettings
from playtrace.models.repair import RepairCounts, RepairPreview
from playtrace.store.db import Database


class RebuildService:
    def plan(
        self,
        db_path: Path,
        settings: ReconstructionSettings | None = None,
    ) -> RepairPreview:
        db = Database(db_path)
        db.bootstrap()
        current_titles = db.load_titles(
            sort_by="runtime",
            classification=None,
            launcher=None,
            limit=10_000,
        )
        current_sessions = [session for _, session in db.load_sessions(title=None, days=3650, limit=10_000)]
        _, proposed_sessions, proposed_titles = db.build_reconstruction_state(settings=settings)

        title_changes = self._title_changes(current_titles, proposed_titles)
        session_changes = self._session_changes(current_sessions, proposed_sessions)
        remaining_duplicate_groups = len(db._duplicate_groups(proposed_titles, threshold=0.75))
        unresolved: list[str] = []
        if remaining_duplicate_groups:
            unresolved.append(
                f"{remaining_duplicate_groups} suspected duplicate title group(s) would remain after repair."
            )

        return RepairPreview(
            counts=RepairCounts(
                merged_titles=max(len(current_titles) - len(proposed_titles), 0),
                changed_titles=len(title_changes),
                changed_sessions=len(session_changes),
                remaining_duplicate_groups=remaining_duplicate_groups,
            ),
            title_changes=title_changes,
            session_changes=session_changes,
            unresolved=unresolved,
        )

    def apply(
        self,
        db_path: Path,
        *,
        preview: RepairPreview,
        confirmed: bool,
        settings: ReconstructionSettings | None = None,
    ) -> RepairPreview:
        if not confirmed:
            raise PermissionError("Repair apply requires --yes.")
        db = Database(db_path)
        db.bootstrap()
        db.rebuild_from_artifacts_and_mappings(settings=settings)
        return preview

    def _title_changes(self, current_titles, proposed_titles) -> list[str]:
        current_lookup = {title.title_id: title.title for title in current_titles}
        proposed_lookup = {title.title_id: title.title for title in proposed_titles}
        changes: list[str] = []
        for title_id in sorted(current_lookup.keys() - proposed_lookup.keys()):
            changes.append(f"remove title {current_lookup[title_id]}")
        for title_id in sorted(proposed_lookup.keys() - current_lookup.keys()):
            changes.append(f"add title {proposed_lookup[title_id]}")
        for title_id in sorted(current_lookup.keys() & proposed_lookup.keys()):
            if current_lookup[title_id] != proposed_lookup[title_id]:
                changes.append(
                    f"rename title {current_lookup[title_id]} -> {proposed_lookup[title_id]}"
                )
        return changes

    def _session_changes(self, current_sessions, proposed_sessions) -> list[str]:
        current_ids = {session.session_id for session in current_sessions}
        proposed_ids = {session.session_id for session in proposed_sessions}
        changes: list[str] = []
        for session_id in sorted(current_ids - proposed_ids):
            changes.append(f"remove session {session_id}")
        for session_id in sorted(proposed_ids - current_ids):
            changes.append(f"add session {session_id}")
        return changes
