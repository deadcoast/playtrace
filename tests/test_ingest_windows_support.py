from __future__ import annotations

import struct
from datetime import datetime, timezone

from playtrace.ingest.windows_support import (
    expand_userassist_entry,
    normalize_security_event_row,
    parse_userassist_binary,
)


def test_expand_userassist_entry_expands_known_folder_guid(monkeypatch) -> None:
    monkeypatch.setenv("ProgramW6432", r"C:\Program Files")

    expanded = expand_userassist_entry(
        r"{6D809377-6AF0-444B-8957-A3773F02200E}\LGHUB\lghub.exe"
    )

    assert expanded == r"C:\Program Files\LGHUB\lghub.exe"


def test_parse_userassist_binary_extracts_counts_and_last_run() -> None:
    payload = bytearray(72)
    expected_last_run = datetime(2026, 4, 16, 8, 40, 52, 798000, tzinfo=timezone.utc)
    filetime = int(expected_last_run.timestamp() * 10_000_000) + 116444736000000000
    struct.pack_into("<I", payload, 4, 19)
    struct.pack_into("<I", payload, 8, 24034000)
    struct.pack_into("<Q", payload, 60, filetime)

    run_count, focus_time_ms, last_run = parse_userassist_binary(bytes(payload))

    assert run_count == 19
    assert focus_time_ms == 24034000
    assert last_run == expected_last_run.isoformat()


def test_normalize_security_event_row_parses_hex_process_ids() -> None:
    normalized = normalize_security_event_row(
        {
            "event_id": 4688,
            "timestamp": "2026-04-17T20:00:00+00:00",
            "pid": "0x3bd8",
            "parent_pid": "0x10",
            "exe_path": r"C:\Games\Balatro\balatro.exe",
            "command_line": r"\"C:\Games\Balatro\balatro.exe\"",
            "user_sid": "S-1-5-21-demo",
        }
    )

    assert normalized == {
        "event_id": 4688,
        "timestamp": "2026-04-17T20:00:00+00:00",
        "pid": 15320,
        "parent_pid": 16,
        "exe_path": r"C:\Games\Balatro\balatro.exe",
        "command_line": r"\"C:\Games\Balatro\balatro.exe\"",
        "user_sid": "S-1-5-21-demo",
    }
