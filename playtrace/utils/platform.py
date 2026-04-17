from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(slots=True)
class PlatformInfo:
    windows_version: str | None
    system_directory: Path | None
    program_files: Path | None
    user_profile: Path | None


class PlatformDetector:
    _cached_info: ClassVar[PlatformInfo | None] = None

    @classmethod
    def detect(cls) -> PlatformInfo:
        if cls._cached_info is not None:
            return cls._cached_info

        if os.name != "nt":
            cls._cached_info = PlatformInfo(
                windows_version=None,
                system_directory=None,
                program_files=None,
                user_profile=None,
            )
            return cls._cached_info

        cls._cached_info = PlatformInfo(
            windows_version=cls._detect_windows_version(),
            system_directory=cls._get_system_directory(),
            program_files=cls._get_program_files(),
            user_profile=cls._get_user_profile(),
        )
        return cls._cached_info

    @staticmethod
    def _detect_windows_version() -> str | None:
        version = platform.win32_ver()[0]
        return version or None

    @staticmethod
    def _get_system_directory() -> Path | None:
        system_root = os.environ.get("SystemRoot")
        if not system_root:
            return None
        return Path(system_root) / "System32"

    @staticmethod
    def _get_program_files() -> Path | None:
        value = os.environ.get("ProgramFiles")
        return Path(value) if value else None

    @staticmethod
    def _get_user_profile() -> Path | None:
        value = os.environ.get("USERPROFILE")
        return Path(value) if value else None
