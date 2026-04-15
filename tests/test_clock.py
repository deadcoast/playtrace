from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st

from playtrace.utils.clock import Clock


def _fixed_timezones() -> st.SearchStrategy[timezone]:
    return st.integers(min_value=-23 * 60, max_value=23 * 60).map(
        lambda minutes: timezone(timedelta(minutes=minutes))
    )


def test_clock_utc_now_returns_aware_utc_datetime() -> None:
    current = Clock.utc_now()

    assert current.tzinfo is not None
    assert current.utcoffset() == timezone.utc.utcoffset(current)


def test_clock_to_utc_assumes_naive_datetimes_are_already_utc() -> None:
    value = datetime(2026, 4, 14, 15, 30, 45)

    assert Clock.to_utc(value) == datetime(2026, 4, 14, 15, 30, 45, tzinfo=timezone.utc)


def test_clock_to_utc_returns_none_for_none() -> None:
    assert Clock.to_utc(None) is None


@given(st.datetimes(timezones=_fixed_timezones()))
def test_clock_to_utc_preserves_instant_for_aware_datetimes(value: datetime) -> None:
    assert Clock.to_utc(value) == value.astimezone(timezone.utc)


def test_clock_parse_iso8601_assumes_naive_strings_are_utc() -> None:
    assert Clock.parse_iso8601("2026-04-14T15:30:45") == datetime(
        2026,
        4,
        14,
        15,
        30,
        45,
        tzinfo=timezone.utc,
    )


def test_clock_parse_iso8601_returns_none_for_none() -> None:
    assert Clock.parse_iso8601(None) is None


@given(st.datetimes(timezones=_fixed_timezones()))
def test_clock_parse_iso8601_returns_timezone_aware_utc_datetimes(value: datetime) -> None:
    parsed = Clock.parse_iso8601(value.isoformat())

    assert parsed == value.astimezone(timezone.utc)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_clock_format_iso8601_returns_none_for_none() -> None:
    assert Clock.format_iso8601(None) is None


@given(st.one_of(st.datetimes(timezones=st.none()), st.datetimes(timezones=_fixed_timezones())))
def test_clock_format_iso8601_normalizes_datetimes_to_utc(value: datetime) -> None:
    assert Clock.format_iso8601(value) == Clock.to_utc(value).isoformat()


@given(st.datetimes(timezones=_fixed_timezones()))
def test_clock_round_trip_preserves_aware_datetimes(value: datetime) -> None:
    converted = Clock.to_utc(value)
    formatted = Clock.format_iso8601(converted)

    assert Clock.parse_iso8601(formatted) == converted
