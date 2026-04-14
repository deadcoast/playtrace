from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from playtrace.models.evidence import EvidenceRecord
from playtrace.models.enums import EvidenceType, RuntimeConfidence
from playtrace.models.session import SessionRecord
from playtrace.normalize.identity import IdentityNormalizer


@dataclass(slots=True)
class SessionMergeConfig:
    dedupe_window: timedelta = timedelta(minutes=2)


class SessionMerger:
    def __init__(
        self,
        config: SessionMergeConfig | None = None,
        normalizer: IdentityNormalizer | None = None,
    ) -> None:
        self.config = config or SessionMergeConfig()
        self.normalizer = normalizer or IdentityNormalizer()

    def build_sessions(self, records: list[EvidenceRecord]) -> list[SessionRecord]:
        sessions: list[SessionRecord] = []
        open_starts: dict[tuple[int | None, str | None, str], list[EvidenceRecord]] = defaultdict(list)

        for record in sorted(records, key=self._sort_key):
            if record.evidence_type == EvidenceType.PROCESS_START:
                open_starts[self._pair_key(record)].append(record)
                continue

            if record.evidence_type != EvidenceType.PROCESS_EXIT:
                continue

            pair_key = self._pair_key(record)
            starts = open_starts.get(pair_key, [])
            if not starts:
                continue

            start = starts.pop(0)
            sessions.append(self._build_exact_session(start, record))

        for starts in open_starts.values():
            for start in starts:
                sessions.append(self._build_partial_session(start))

        return sessions

    def _pair_key(self, record: EvidenceRecord) -> tuple[int | None, str | None, str]:
        pid = record.value.get("pid")
        if pid is not None:
            pid = int(pid)
        user_sid = record.value.get("user_sid")
        if user_sid is not None:
            user_sid = str(user_sid)
        return pid, user_sid, self.normalizer.build_key(record)

    def _build_exact_session(
        self,
        start: EvidenceRecord,
        end: EvidenceRecord,
    ) -> SessionRecord:
        duration_seconds = None
        if start.observed_at and end.observed_at:
            delta = end.observed_at - start.observed_at
            duration_seconds = max(int(delta.total_seconds()), 0)

        parent_pid = start.value.get("parent_pid")
        parent_chain = [str(parent_pid)] if parent_pid is not None else []

        return SessionRecord(
            session_id=self._session_id(start),
            title_id=None,
            exe_id=self.normalizer.build_key(start),
            user_sid=self._string_value(start, "user_sid"),
            started_at=start.observed_at,
            ended_at=end.observed_at,
            duration_seconds=duration_seconds,
            confidence=RuntimeConfidence.EXACT,
            evidence_sources=sorted({start.source.value, end.source.value}),
            evidence_ids=[start.evidence_id, end.evidence_id],
            parent_chain=parent_chain,
        )

    def _build_partial_session(self, start: EvidenceRecord) -> SessionRecord:
        parent_pid = start.value.get("parent_pid")
        parent_chain = [str(parent_pid)] if parent_pid is not None else []

        return SessionRecord(
            session_id=self._session_id(start),
            title_id=None,
            exe_id=self.normalizer.build_key(start),
            user_sid=self._string_value(start, "user_sid"),
            started_at=start.observed_at,
            ended_at=None,
            duration_seconds=None,
            confidence=RuntimeConfidence.UNKNOWN,
            evidence_sources=[start.source.value],
            evidence_ids=[start.evidence_id],
            parent_chain=parent_chain,
        )

    def _session_id(self, record: EvidenceRecord) -> str:
        pid = record.value.get("pid", "unknown")
        timestamp = record.observed_at or datetime.min.replace(tzinfo=timezone.utc)
        return f"{self.normalizer.build_key(record)}:session:{pid}:{int(timestamp.timestamp())}"

    def _sort_key(self, record: EvidenceRecord) -> tuple[datetime, str]:
        observed_at = record.observed_at or datetime.min.replace(tzinfo=timezone.utc)
        return observed_at, record.evidence_id

    def _string_value(self, record: EvidenceRecord, key: str) -> str | None:
        value = record.value.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None
