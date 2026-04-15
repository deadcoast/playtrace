from __future__ import annotations

import os
import re
from pathlib import PureWindowsPath


class PathNormalizer:
    _ENV_VAR_PATTERN = re.compile(r"%([^%]+)%")

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
        return self._ENV_VAR_PATTERN.sub(self._expand_variable, path)

    def _to_absolute(self, path: str) -> str:
        windows_path = PureWindowsPath(path)
        if windows_path.is_absolute():
            return str(windows_path)

        cwd = self._windows_cwd()
        if cwd is None:
            return str(windows_path)

        return str(PureWindowsPath(cwd) / windows_path)

    def _to_backslashes(self, path: str) -> str:
        return path.replace("/", "\\")

    def _expand_variable(self, match: re.Match[str]) -> str:
        variable_name = match.group(1)
        return os.environ.get(variable_name, match.group(0))

    def _windows_cwd(self) -> str | None:
        current = str(PureWindowsPath(os.getcwd()))
        if not PureWindowsPath(current).is_absolute():
            return None
        return current
