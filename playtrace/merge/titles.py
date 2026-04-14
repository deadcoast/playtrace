from __future__ import annotations

from playtrace.models.executable import ExecutableIdentity
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.models.enums import Classification, ConfidenceLevel


class TitleAggregator:
    def build(self, executables: list[ExecutableIdentity], sessions: list[SessionRecord]) -> list[TitleAggregate]:
        title_map: dict[str, TitleAggregate] = {}

        for exe in executables:
            title_name = exe.product_name or (exe.filename.rsplit(".", 1)[0] if exe.filename else exe.exe_id)
            title_id = f"title:{title_name.lower().replace(' ', '_')}"
            title = title_map.setdefault(
                title_id,
                TitleAggregate(
                    title_id=title_id,
                    title=title_name,
                    classification=exe.classification or Classification.UNKNOWN,
                    classification_confidence=exe.classification_confidence or ConfidenceLevel.UNKNOWN,
                    title_confidence=ConfidenceLevel.MEDIUM,
                    launcher=None,
                ),
            )
            title.executable_ids.append(exe.exe_id)
            if exe.first_seen and (title.first_seen is None or exe.first_seen < title.first_seen):
                title.first_seen = exe.first_seen
            if exe.last_seen and (title.last_seen is None or exe.last_seen > title.last_seen):
                title.last_seen = exe.last_seen

        for session in sessions:
            for title in title_map.values():
                if session.exe_id in title.executable_ids:
                    if session.duration_seconds:
                        title.runtime.confirmed_seconds += session.duration_seconds
                    title.runtime.foreground_seconds += session.foreground_seconds
                    title.launches.confirmed += 1
                    break

        for title in title_map.values():
            title.runtime.confidence = ConfidenceLevel.HIGH if title.runtime.confirmed_seconds else ConfidenceLevel.UNKNOWN
            title.launches.confidence = ConfidenceLevel.HIGH if title.launches.confirmed else ConfidenceLevel.UNKNOWN

        return list(title_map.values())