from __future__ import annotations

<<<<<<< HEAD
import json
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from playtrace.models.enums import ConfidenceLevel
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class SecurityEvent:
    record_id: int
    event_id: int
    time_created: datetime
    process_id: int | None
    process_name: str | None
    parent_process_id: int | None
    user_sid: str | None


class SecurityLogParser:
    name = "security_log"

    def is_available(self) -> bool:
        return os.name == "nt" and self._can_read_log()

    def parse_sessions(self, days: int) -> list[SessionRecord]:
        events = self._fetch_events(days)
        return self._pair_sessions(events)

    def _can_read_log(self) -> bool:
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-WinEvent -LogName Security -MaxEvents 1 | Out-Null",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            return False

    def _fetch_events(self, days: int) -> list[SecurityEvent]:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
        script = rf"""
$ProgressPreference = 'SilentlyContinue'
$start = [datetime]'{{0}}'
Get-WinEvent -FilterHashtable @{{ LogName='Security'; Id=4688,4689; StartTime=$start }} |
ForEach-Object {{
    [PSCustomObject]@{{
        RecordId = $_.RecordId
        Id = $_.Id
        TimeCreated = $_.TimeCreated.ToString('o')
        Properties = @($_.Properties | ForEach-Object {{ $_.Value }})
    }}
}} | ConvertTo-Json -Depth 5 -Compress
""".format(start)
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = result.stdout.strip()
        if not payload:
            return []

        decoded = json.loads(payload)
        rows = decoded if isinstance(decoded, list) else [decoded]
        events: list[SecurityEvent] = []
        for row in rows:
            try:
                event = self._parse_event(row)
            except Exception:
                continue
            if event and event.process_name:
                events.append(event)
        events.sort(key=lambda item: (item.time_created, item.record_id))
        return events

    def _parse_event(self, row: dict) -> SecurityEvent | None:
        event_id = int(row["Id"])
        values = row.get("Properties") or []
        if event_id == 4688:
            process_id = self._coerce_pid(self._safe_get(values, 4))
            process_name = self._normalize_path(self._safe_get(values, 5))
            parent_process_id = self._coerce_pid(self._safe_get(values, 7))
            user_sid = self._as_text(self._safe_get(values, 0))
        elif event_id == 4689:
            process_id = self._coerce_pid(self._safe_get(values, 5))
            process_name = self._normalize_path(self._safe_get(values, 6))
            parent_process_id = None
            user_sid = self._as_text(self._safe_get(values, 0))
        else:
            return None

        return SecurityEvent(
            record_id=int(row["RecordId"]),
            event_id=event_id,
            time_created=datetime.fromisoformat(row["TimeCreated"]),
            process_id=process_id,
            process_name=process_name,
            parent_process_id=parent_process_id,
            user_sid=user_sid,
        )

    def _pair_sessions(self, events: list[SecurityEvent]) -> list[SessionRecord]:
        starts: dict[tuple[int, str], list[SecurityEvent]] = defaultdict(list)
        sessions: list[SessionRecord] = []

        for event in events:
            if event.process_id is None or not event.process_name:
                continue
            key = (event.process_id, event.process_name.lower())
            if event.event_id == 4688:
                starts[key].append(event)
                continue

            if event.event_id != 4689:
                continue
            start_event = self._pop_start(starts, key, event.time_created)
            if start_event is None:
                continue

            duration = int((event.time_created - start_event.time_created).total_seconds())
            if duration < 0:
                continue

            exe_path = start_event.process_name
            exe_name = Path(exe_path).name if exe_path else "unknown.exe"
            exe_id = exe_path.lower()
            title = self._derive_title(exe_name)
            confidence = ConfidenceLevel.HIGH if duration > 0 else ConfidenceLevel.MEDIUM

            sessions.append(
                SessionRecord(
                    session_id=f"security:{start_event.record_id}:{event.record_id}",
                    title_id=self._make_title_id(title),
                    exe_id=exe_id,
                    user_sid=start_event.user_sid or event.user_sid,
                    started_at=start_event.time_created,
                    ended_at=event.time_created,
                    duration_seconds=duration,
                    confidence=confidence,
                    evidence_sources=["security_log"],
                    parent_chain=[f"pid:{start_event.parent_process_id}"] if start_event.parent_process_id else [],
                )
            )

        return sessions

    def _pop_start(
        self,
        starts: dict[tuple[int, str], list[SecurityEvent]],
        key: tuple[int, str],
        end_time: datetime,
    ) -> SecurityEvent | None:
        candidates = starts.get(key) or []
        while candidates:
            event = candidates.pop(0)
            if event.time_created <= end_time:
                return event
        return None

    def _derive_title(self, exe_name: str) -> str:
        stem = Path(exe_name).stem.replace("_", " ").replace("-", " ").strip()
        if not stem:
            return "Unknown"
        if stem.lower().endswith("64") and len(stem) > 2:
            stem = stem[:-2].rstrip()
        return " ".join(part.capitalize() for part in stem.split())

    def _make_title_id(self, title: str) -> str:
        normalized = "_".join(title.lower().split())
        return f"title:{normalized}"

    def _safe_get(self, values: list[object], index: int) -> object | None:
        if index < 0 or index >= len(values):
            return None
        return values[index]

    def _as_text(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _normalize_path(self, value: object | None) -> str | None:
        text = self._as_text(value)
        if not text:
            return None
        return text.strip('"')

    def _coerce_pid(self, value: object | None) -> int | None:
        text = self._as_text(value)
        if not text:
            return None
        try:
            if text.lower().startswith("0x"):
                return int(text, 16)
            return int(text)
        except ValueError:
            return None
=======
from playtrace.models.evidence import EvidenceRecord, RawArtifact
from playtrace.models.enums import EvidenceStrength, EvidenceType, SourceName


class SecurityLogParser:
    name = SourceName.SECURITY_LOG.value

    def parse(self, artifacts: list[RawArtifact]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for index, artifact in enumerate(artifacts, start=1):
            event_id = artifact.payload.get("event_id")
            evidence_type = None
            if event_id == 4688:
                evidence_type = EvidenceType.PROCESS_START
            elif event_id == 4689:
                evidence_type = EvidenceType.PROCESS_EXIT

            if evidence_type is None:
                continue

            records.append(
                EvidenceRecord(
                    evidence_id=f"evidence:{self.name}:{index}:{artifact.artifact_id}",
                    artifact_id=artifact.artifact_id,
                    source=SourceName.SECURITY_LOG,
                    evidence_type=evidence_type,
                    observed_at=artifact.observed_at,
                    strength=EvidenceStrength.EXACT,
                    value=dict(artifact.payload),
                )
            )
        return records
>>>>>>> 5826d2c01e206f624bf2fa0731bedd097ed65711
