from __future__ import annotations

import os
from pathlib import PureWindowsPath


class PathNormalizer:
    def normalize(self, path: str | None) -> str | None:
        if path is None:
            return None

        text = path.strip()
        if not text:
            return None

        normalized = self._strip_quotes(text).strip()
        if not normalized:
            return None

        normalized = self._expand_variables(normalized)
        normalized = self._to_backslashes(normalized)
        normalized = self._to_absolute(normalized)
        return str(PureWindowsPath(normalized)).lower()

    def _strip_quotes(self, path: str) -> str:
        if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
            return path[1:-1]
        return path

    def _expand_variables(self, path: str) -> str:
        return os.path.expandvars(path)

    def _to_absolute(self, path: str) -> str:
        return path if PureWindowsPath(path).is_absolute() else os.path.abspath(path)

    def _to_backslashes(self, path: str) -> str:
        return path.replace("/", "\\")
