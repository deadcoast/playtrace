from __future__ import annotations

from dataclasses import dataclass, field

from playtrace.models.enums import SourceName


@dataclass(slots=True)
class ConfigModel:
    session_merge_dedupe_window_minutes: int = 2
    default_sources: list[str] = field(default_factory=list)
    classification_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate_merge_window()
        self._validate_sources()

    def _validate_merge_window(self) -> None:
        if self.session_merge_dedupe_window_minutes <= 0:
            raise ValueError("session_merge_dedupe_window_minutes must be positive")

    def _validate_sources(self) -> None:
        for source in self.default_sources:
            try:
                SourceName(source)
            except ValueError as exc:
                raise ValueError(f"default_sources contains invalid source: {source}") from exc


Config_Model = ConfigModel
