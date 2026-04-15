from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from playtrace.config.models import Config_Model


class ConfigLoader:
    def load(self, path: Path | None = None) -> Config_Model:
        if path is None:
            return Config_Model()

        candidate = Path(path)
        if not candidate.exists():
            return Config_Model()

        data = self._parse_toml(candidate)
        return Config_Model(**self._apply_defaults(data))

    def _parse_toml(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"Invalid TOML in {path}: {exc}") from exc

    def _apply_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        session = data.get("session")
        sources = data.get("sources")
        classification = data.get("classification")

        session_data = session if isinstance(session, dict) else {}
        source_data = sources if isinstance(sources, dict) else {}
        classification_data = classification if isinstance(classification, dict) else {}

        return {
            "session_merge_dedupe_window_minutes": session_data.get(
                "merge_dedupe_window_minutes",
                2,
            ),
            "default_sources": source_data.get("default", []),
            "classification_overrides": classification_data.get("overrides", {}),
        }
