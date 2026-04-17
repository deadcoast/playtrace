from __future__ import annotations

from datetime import datetime, timedelta, timezone

from playtrace.utils.clock import Clock


def test_utc_now_returns_timezone_aware_utc_datetime() -> None:
    now = Clock.utc_now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_to_utc_assumes_naive_datetime_is_already_utc() -> None:
    naive = datetime(2026, 4, 17, 19, 45, 0)

    assert Clock.to_utc(naive) == datetime(2026, 4, 17, 19, 45, 0, tzinfo=timezone.utc)


def test_to_utc_preserves_instant_for_aware_datetime() -> None:
    aware = datetime(2026, 4, 17, 12, 45, 0, tzinfo=timezone(timedelta(hours=-7)))

    assert Clock.to_utc(aware) == datetime(2026, 4, 17, 19, 45, 0, tzinfo=timezone.utc)


def test_parse_and_format_iso8601_round_trip_through_utc() -> None:
    original = datetime(2026, 4, 17, 12, 45, 0, tzinfo=timezone(timedelta(hours=-7)))

    formatted = Clock.format_iso8601(original)

    assert formatted == "2026-04-17T19:45:00+00:00"
    assert Clock.parse_iso8601(formatted) == datetime(
        2026,
        4,
        17,
        19,
        45,
        0,
        tzinfo=timezone.utc,
    )


def test_clock_methods_are_null_safe() -> None:
    assert Clock.to_utc(None) is None
    assert Clock.format_iso8601(None) is None
    assert Clock.parse_iso8601(None) is None
