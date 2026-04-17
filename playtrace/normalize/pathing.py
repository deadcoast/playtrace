from __future__ import annotations

import ntpath
import os
import re
from pathlib import Path, PureWindowsPath


class PathNormalizer:
    _WINDOWS_ENV_VAR_PATTERN = re.compile(r"%([^%]+)%")

    def normalize(self, path: str | None) -> str | None:
        if path is None:
            return None

        stripped = self._strip_quotes(path.strip())
        if not stripped:
            return None

        expanded = self._expand_variables(stripped)
        absolute = self._to_absolute(self._to_backslashes(expanded))
        return str(PureWindowsPath(absolute)).lower()

    def _strip_quotes(self, path: str) -> str:
        if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
            return path[1:-1].strip()
        return path

    def _expand_variables(self, path: str) -> str:
        expanded = os.path.expandvars(path)
        return self._WINDOWS_ENV_VAR_PATTERN.sub(
            lambda match: os.environ.get(match.group(1), match.group(0)),
            expanded,
        )

    def _to_absolute(self, path: str) -> str:
        if (
            ntpath.isabs(path)
            or path.startswith("\\\\")
            or self._WINDOWS_ENV_VAR_PATTERN.search(path)
        ):
            return path
        return str(Path(path).resolve())

    def _to_backslashes(self, path: str) -> str:
        return path.replace("/", "\\")
