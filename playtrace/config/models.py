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
        self._validate_classification_overrides()

    def _validate_merge_window(self) -> None:
        value = self.session_merge_dedupe_window_minutes
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("session_merge_dedupe_window_minutes must be an integer")
        if value <= 0:
            raise ValueError("session_merge_dedupe_window_minutes must be positive")

    def _validate_sources(self) -> None:
        if not isinstance(self.default_sources, list):
            raise TypeError("default_sources must be a list of source names")

        valid_sources = {source.value for source in SourceName}
        for source in self.default_sources:
            if not isinstance(source, str):
                raise TypeError("default_sources must contain strings")
            if source not in valid_sources:
                raise ValueError(f"default_sources contains invalid source name: {source}")

    def _validate_classification_overrides(self) -> None:
        if not isinstance(self.classification_overrides, dict):
            raise TypeError("classification_overrides must be a mapping of paths to classifications")

        for key, value in self.classification_overrides.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError("classification_overrides must map strings to strings")


# Backward-compatible alias for the spec bundle's original public name.
Config_Model = ConfigModel
