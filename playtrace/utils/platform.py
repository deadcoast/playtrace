from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(slots=True, frozen=True)
class PlatformInfo:
    windows_version: str | None
    system_directory: str | None
    program_files: str | None
    user_profile: str | None


class PlatformDetector:
    _cached: ClassVar[PlatformInfo | None] = None

    @classmethod
    def detect(cls) -> PlatformInfo:
        if cls._cached is not None:
            return cls._cached

        if platform.system() != "Windows":
            cls._cached = PlatformInfo(
                windows_version=None,
                system_directory=None,
                program_files=None,
                user_profile=None,
            )
            return cls._cached

        system_root = cls._clean(os.environ.get("SystemRoot") or os.environ.get("WINDIR"))
        system_directory = str(Path(system_root) / "System32") if system_root else None

        cls._cached = PlatformInfo(
            windows_version=cls._detect_windows_version(),
            system_directory=system_directory,
            program_files=cls._clean(os.environ.get("ProgramFiles")),
            user_profile=cls._clean(os.environ.get("USERPROFILE")),
        )
        return cls._cached

    @staticmethod
    def _detect_windows_version() -> str | None:
        version = platform.win32_ver()[0].strip()
        return version or None

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None
