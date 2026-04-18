from __future__ import annotations

import codecs
import json
import os
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import PureWindowsPath
from typing import Mapping

if os.name == "nt":  # pragma: no branch
    import winreg
else:  # pragma: no cover
    winreg = None


_USERASSIST_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
_WINDOWS_EPOCH = 116444736000000000


def expand_userassist_entry(entry: str) -> str | None:
    normalized = entry.strip().replace("/", "\\")
    if not normalized or ".exe" not in normalized.lower():
        return None

    if _looks_like_windows_path(normalized):
        return str(PureWindowsPath(normalized))

    if normalized.startswith("{") and "}\\" in normalized:
        prefix, suffix = normalized.split("}\\", 1)
        base_path = _known_folder_paths().get(prefix.casefold() + "}")
        if base_path:
            return str(PureWindowsPath(base_path) / PureWindowsPath(suffix))

    return None


def parse_userassist_binary(data: bytes) -> tuple[int | None, int | None, str | None]:
    run_count = struct.unpack_from("<I", data, 4)[0] if len(data) >= 8 else None
    focus_time_ms = struct.unpack_from("<I", data, 8)[0] if len(data) >= 12 else None
    filetime = struct.unpack_from("<Q", data, 60)[0] if len(data) >= 68 else 0
    return run_count, focus_time_ms, _filetime_to_iso(filetime)


def collect_userassist_payloads() -> list[dict[str, object]]:
    if winreg is None:
        return []

    aggregated: dict[str, dict[str, object]] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _USERASSIST_ROOT) as root:
            subkey_count = winreg.QueryInfoKey(root)[0]
            for index in range(subkey_count):
                subkey_name = winreg.EnumKey(root, index)
                with winreg.OpenKey(root, subkey_name + r"\Count") as count_key:
                    value_count = winreg.QueryInfoKey(count_key)[1]
                    for value_index in range(value_count):
                        name, data, _kind = winreg.EnumValue(count_key, value_index)
                        if not isinstance(data, bytes):
                            continue

                        decoded = codecs.decode(name, "rot_13")
                        exe_path = expand_userassist_entry(decoded)
                        if not exe_path:
                            continue

                        run_count, focus_time_ms, last_run = parse_userassist_binary(data)
                        if not any(
                            value not in (None, 0, "")
                            for value in (run_count, focus_time_ms, last_run)
                        ):
                            continue

                        payload = aggregated.setdefault(
                            exe_path,
                            {
                                "entry": decoded,
                                "exe_path": exe_path,
                                "run_count": int(run_count or 0),
                                "focus_time_ms": int(focus_time_ms or 0),
                                "last_run": last_run,
                            },
                        )
                        payload["run_count"] = max(
                            int(payload["run_count"]),
                            int(run_count or 0),
                        )
                        payload["focus_time_ms"] = max(
                            int(payload["focus_time_ms"]),
                            int(focus_time_ms or 0),
                        )
                        payload["last_run"] = _later_iso(payload.get("last_run"), last_run)
    except OSError:
        return []

    return sorted(
        aggregated.values(),
        key=lambda payload: payload.get("last_run") or "",
        reverse=True,
    )


def normalize_security_event_row(row: Mapping[str, object]) -> dict[str, object] | None:
    exe_path = _string_or_none(row.get("exe_path"))
    if not exe_path or not exe_path.lower().endswith(".exe"):
        return None

    timestamp = _string_or_none(row.get("timestamp"))
    event_id = _coerce_int(row.get("event_id"))
    if timestamp is None or event_id is None:
        return None

    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "pid": _coerce_int(row.get("pid")),
        "parent_pid": _coerce_int(row.get("parent_pid")),
        "exe_path": exe_path,
        "command_line": _string_or_none(row.get("command_line")),
        "user_sid": _string_or_none(row.get("user_sid")),
    }


def query_security_events(max_events: int) -> list[dict[str, object]]:
    if os.name != "nt":
        return []

    script = rf"""
$events = Get-WinEvent -FilterHashtable @{{LogName='Security'; Id=4688,4689}} -MaxEvents {max_events} -ErrorAction Stop
$rows = foreach ($event in $events) {{
    $xml = [xml]$event.ToXml()
    $data = @{{}}
    foreach ($node in $xml.Event.EventData.Data) {{
        $data[[string]$node.Name] = [string]$node.'#text'
    }}
    [pscustomobject]@{{
        event_id = [int]$event.Id
        timestamp = $event.TimeCreated.ToString('o')
        pid = if ($data['NewProcessId']) {{ $data['NewProcessId'] }} else {{ $data['ProcessId'] }}
        parent_pid = $data['ProcessId']
        exe_path = if ($data['NewProcessName']) {{ $data['NewProcessName'] }} else {{ $data['ProcessName'] }}
        command_line = $data['CommandLine']
        user_sid = if ($data['SubjectUserSid']) {{ $data['SubjectUserSid'] }} else {{ $data['TargetUserSid'] }}
    }}
}}
$rows | ConvertTo-Json -Compress -Depth 4
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        if "No events were found" in stderr:
            return []
        raise RuntimeError(stderr or "security log collection failed")

    stdout = (result.stdout or "").strip()
    if not stdout:
        return []

    payload = json.loads(stdout)
    rows = payload if isinstance(payload, list) else [payload]
    events: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = normalize_security_event_row(row)
        if normalized is not None:
            events.append(normalized)
    return events


def _known_folder_paths() -> dict[str, str]:
    return {
        "{1ac14e77-02e7-4e5d-b744-2eb1ae5198b7}": os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32",
        ),
        "{6d809377-6af0-444b-8957-a3773f02200e}": (
            os.environ.get("ProgramW6432")
            or os.environ.get("ProgramFiles")
            or r"C:\Program Files"
        ),
        "{7c5a40ef-a0fb-4bfc-874a-c0f2e0b9fa8e}": (
            os.environ.get("ProgramFiles(x86)")
            or os.environ.get("ProgramFiles")
            or r"C:\Program Files (x86)"
        ),
    }


def _looks_like_windows_path(value: str) -> bool:
    return len(value) > 2 and value[1] == ":" and value[2] == "\\"


def _filetime_to_iso(filetime: int) -> str | None:
    if not filetime or filetime < _WINDOWS_EPOCH:
        return None

    unix_timestamp = (filetime - _WINDOWS_EPOCH) / 10_000_000
    try:
        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _later_iso(current: object, candidate: str | None) -> str | None:
    current_value = _string_or_none(current)
    if current_value is None:
        return candidate
    if candidate is None:
        return current_value
    return candidate if candidate > current_value else current_value


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value

    text = str(value).strip()
    if not text:
        return None
    base = 16 if text.lower().startswith("0x") else 10
    try:
        return int(text, base)
    except ValueError:
        return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
