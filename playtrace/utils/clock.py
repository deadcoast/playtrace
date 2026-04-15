from __future__ import annotations

from datetime import datetime, timezone


class Clock:
    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def to_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def parse_iso8601(value: str | None) -> datetime | None:
        if value is None:
            return None
        return Clock.to_utc(datetime.fromisoformat(value))

    @staticmethod
    def format_iso8601(value: datetime | None) -> str | None:
        converted = Clock.to_utc(value)
        if converted is None:
            return None
        return converted.isoformat()
