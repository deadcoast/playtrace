from __future__ import annotations

from playtrace.classify.resolver import TitleResolver
from playtrace.merge.confidence import launches_confidence
from playtrace.models.enums import ConfidenceLevel
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import TitleAggregate


class TitleAggregator:
    def __init__(self, resolver: TitleResolver | None = None) -> None:
        self.resolver = resolver or TitleResolver()

    def build(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mappings: list[UserMapping] | None = None,
    ) -> list[TitleAggregate]:
        aggregates: list[TitleAggregate] = []
        resolved_result = self.resolver.resolve(executables, sessions, mappings)
        for resolved in resolved_result.titles:
            title = TitleAggregate(
                title_id=resolved.title_id,
                title=resolved.title,
                classification=resolved.classification,
                classification_confidence=resolved.classification_confidence,
                title_confidence=resolved.title_confidence,
                launcher=resolved.launcher,
                primary_exe_id=resolved.primary_exe_id,
                executable_ids=list(resolved.executable_ids),
                suppressed_executable_ids=list(resolved.suppressed_executable_ids),
            )

            related_sessions = [
                session for session in sessions if session.exe_id in resolved.executable_ids
            ]
            for session in related_sessions:
                if session.duration_seconds:
                    title.runtime.confirmed_seconds += session.duration_seconds
                title.runtime.foreground_seconds += session.foreground_seconds
                title.launches.confirmed += 1
                title.evidence_sources.extend(session.evidence_sources)
                if title.first_seen is None or (
                    session.started_at and session.started_at < title.first_seen
                ):
                    title.first_seen = session.started_at
                session_end = session.ended_at or session.started_at
                if title.last_seen is None or (session_end and session_end > title.last_seen):
                    title.last_seen = session_end

            title.evidence_sources = sorted(set(title.evidence_sources))
            title.runtime.confidence = (
                ConfidenceLevel.HIGH if title.runtime.confirmed_seconds else ConfidenceLevel.UNKNOWN
            )
            title.launches.confidence = launches_confidence(related_sessions)
            aggregates.append(title)

        return aggregates
