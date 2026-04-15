from __future__ import annotations

import platform

import pytest

from playtrace.utils.platform import PlatformDetector, PlatformInfo


@pytest.fixture(autouse=True)
def reset_platform_detector_cache() -> None:
    PlatformDetector._cached = None


def test_platform_detector_detects_windows_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "win32_ver", lambda: ("11", "", "", ""))
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\ryanf")

    assert PlatformDetector.detect() == PlatformInfo(
        windows_version="11",
        system_directory=r"C:\Windows\System32",
        program_files=r"C:\Program Files",
        user_profile=r"C:\Users\ryanf",
    )


def test_platform_detector_returns_none_paths_on_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    assert PlatformDetector.detect() == PlatformInfo(
        windows_version=None,
        system_directory=None,
        program_files=None,
        user_profile=None,
    )


def test_platform_detector_caches_detected_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "win32_ver", lambda: ("10", "", "", ""))
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\ryanf")

    first = PlatformDetector.detect()
    second = PlatformDetector.detect()

    assert first is second


def test_platform_detector_returns_identical_values_on_repeated_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "win32_ver", lambda: ("Server 2019", "", "", ""))
    monkeypatch.setenv("SystemRoot", r"D:\Windows")
    monkeypatch.setenv("ProgramFiles", r"D:\Program Files")
    monkeypatch.setenv("USERPROFILE", r"D:\Users\ryanf")

    first = PlatformDetector.detect()
    second = PlatformDetector.detect()

    assert first == second
