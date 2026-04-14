from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from playtrace.models.artifacts import ArtifactRecord
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class SessionMergeConfig:
    dedupe_window: timedelta = timedelta(minutes=2)


class SessionMerger:
    def __init__(self, config: SessionMergeConfig | None = None) -> None:
        self.config = config or SessionMergeConfig()

    def build_sessions(self, artifacts: list[ArtifactRecord], exe_id_lookup: dict[str, str]) -> list[SessionRecord]:
        # First-pass stub.
        # v1 behavior:
        # - exact session creation for artifacts with both started_at and ended_at
        # - partial sessions for launch-only artifacts
        sessions: list[SessionRecord] = []
        grouped: dict[str, list[ArtifactRecord]] = defaultdict(list)

        for artifact in artifacts:
            key = exe_id_lookup.get(artifact.artifact_id)
            if key:
                grouped[key].append(artifact)

        for exe_id, group in grouped.items():
            for index, artifact in enumerate(group, start=1):
                sessions.append(
                    SessionRecord(
                        session_id=f"{exe_id}:session:{index}",
                        title_id=None,
                        exe_id=exe_id,
                        user_sid=artifact.user_sid,
                        started_at=artifact.started_at or artifact.observed_at,
                        ended_at=artifact.ended_at,
                        duration_seconds=artifact.duration_seconds,
                        foreground_seconds=artifact.foreground_seconds or 0,
                        bytes_in=artifact.bytes_in or 0,
                        bytes_out=artifact.bytes_out or 0,
                        evidence_sources=[artifact.source.value],
                    )
                )

        return sessions