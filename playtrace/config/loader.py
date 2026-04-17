from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from playtrace.config.models import ConfigModel


class ConfigLoader:
    def load(self, path: Path | None = None) -> ConfigModel:
        if path is None or not path.exists():
            return ConfigModel()

        data = self._parse_toml(path)
        return ConfigModel(**self._apply_defaults(data))

    def _parse_toml(self, path: Path) -> dict[str, Any]:
        with path.open("rb") as handle:
            return tomllib.load(handle)

    def _apply_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        session = data.get("session") or {}
        sources = data.get("sources") or {}
        classification = data.get("classification") or {}
        return {
            "session_merge_dedupe_window_minutes": session.get(
                "merge_dedupe_window_minutes",
                2,
            ),
            "default_sources": list(sources.get("default", [])),
            "classification_overrides": dict(classification.get("overrides", {})),
        }
