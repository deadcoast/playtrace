from __future__ import annotations

from datetime import datetime, timezone


class Clock:
    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def to_utc(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def parse_iso8601(iso_string: str | None) -> datetime | None:
        if iso_string is None:
            return None
        text = iso_string.strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text)
        return Clock.to_utc(parsed)

    @staticmethod
    def format_iso8601(dt: datetime | None) -> str | None:
        normalized = Clock.to_utc(dt)
        return normalized.isoformat() if normalized else None
