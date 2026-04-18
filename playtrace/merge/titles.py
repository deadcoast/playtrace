from __future__ import annotations

from collections import defaultdict

from playtrace.classify.resolver import TitleResolver
from playtrace.merge.confidence import launches_confidence
from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import ConfidenceLevel, EvidenceType
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord
from playtrace.models.title import TitleAggregate
from playtrace.normalize.identity import IdentityNormalizer


class TitleAggregator:
    def __init__(self, resolver: TitleResolver | None = None) -> None:
        self.resolver = resolver or TitleResolver()

    def build(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mappings: list[UserMapping] | None = None,
        evidence_records: list[EvidenceRecord] | None = None,
        config_overrides: dict[str, str] | None = None,
    ) -> list[TitleAggregate]:
        aggregates: list[TitleAggregate] = []
        normalizer = IdentityNormalizer()
        evidence_by_executable: dict[str, list[EvidenceRecord]] = defaultdict(list)
        for record in evidence_records or []:
            evidence_by_executable[normalizer.build_key(record)].append(record)

        resolved_result = self.resolver.resolve(
            executables,
            sessions,
            mappings,
            config_overrides=config_overrides,
        )
        for resolved in resolved_result.titles:
            title = TitleAggregate(
                title_id=resolved.title_id,
                title=resolved.title,
                classification=resolved.classification,
                classification_confidence=resolved.classification_confidence,
                title_confidence=resolved.title_confidence,
                launcher=resolved.launcher,
                primary_exe_id=resolved.primary_exe_id,
                alternate_titles=list(resolved.alternate_titles),
                notes=list(resolved.notes),
                executable_ids=list(resolved.executable_ids),
                suppressed_executable_ids=list(resolved.suppressed_executable_ids),
            )

            related_sessions = [
                session for session in sessions if session.exe_id in resolved.executable_ids
            ]
            related_evidence = [
                record
                for exe_id in resolved.executable_ids
                for record in evidence_by_executable.get(exe_id, [])
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

            for record in related_evidence:
                title.evidence_sources.append(record.source.value)
                if title.first_seen is None or (
                    record.observed_at and record.observed_at < title.first_seen
                ):
                    title.first_seen = record.observed_at
                if title.last_seen is None or (
                    record.observed_at and record.observed_at > title.last_seen
                ):
                    title.last_seen = record.observed_at

                if record.evidence_type is EvidenceType.INTERACTIVE_LAUNCH:
                    title.launches.gui += 1
                elif record.evidence_type is EvidenceType.RECENT_EXECUTION:
                    title.launches.inferred += 1
                elif record.evidence_type is EvidenceType.FOREGROUND_USAGE:
                    focus_time_ms = record.value.get("focus_time_ms")
                    if focus_time_ms is not None:
                        title.runtime.foreground_seconds += int(focus_time_ms) // 1000

            title.evidence_sources = sorted(set(title.evidence_sources))
            title.runtime.confidence = (
                ConfidenceLevel.HIGH if title.runtime.confirmed_seconds else ConfidenceLevel.UNKNOWN
            )
            if related_sessions:
                title.launches.confidence = launches_confidence(related_sessions)
            elif title.launches.gui:
                title.launches.confidence = ConfidenceLevel.HIGH
            elif title.launches.inferred:
                title.launches.confidence = ConfidenceLevel.MEDIUM
            else:
                title.launches.confidence = ConfidenceLevel.UNKNOWN
            aggregates.append(title)

        return aggregates
