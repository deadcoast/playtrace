from __future__ import annotations

import os
import platform
from pathlib import Path, PurePosixPath

import playtrace.utils.platform as platform_module

from playtrace.utils.platform import PlatformDetector


def test_detect_caches_platform_info(monkeypatch) -> None:
    PlatformDetector._cached_info = None
    monkeypatch.setattr(os, "name", "nt", raising=False)
    monkeypatch.setattr(platform, "win32_ver", lambda: ("11", "", "", ""))
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Ryan")

    first = PlatformDetector.detect()
    second = PlatformDetector.detect()

    assert first is second
    assert first.windows_version == "11"
    assert first.system_directory == Path(r"C:\Windows\System32")
    assert first.program_files == Path(r"C:\Program Files")
    assert first.user_profile == Path(r"C:\Users\Ryan")


def test_detect_returns_empty_windows_fields_on_non_windows(monkeypatch) -> None:
    PlatformDetector._cached_info = None
    monkeypatch.setattr(os, "name", "posix", raising=False)

    info = PlatformDetector.detect()

    assert info.windows_version is None
    assert info.system_directory is None
    assert info.program_files is None
    assert info.user_profile is None


def test_get_system_directory_preserves_windows_separators_across_path_flavors(monkeypatch) -> None:
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setattr(platform_module, "Path", PurePosixPath)

    system_directory = PlatformDetector._get_system_directory()

    assert str(system_directory) == r"C:\Windows\System32"
