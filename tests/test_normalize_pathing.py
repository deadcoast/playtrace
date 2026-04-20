from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath

import playtrace.normalize.pathing as pathing_module
from playtrace.normalize.pathing import PathNormalizer


class UnstableItemsEnviron(dict):
    def items(self):  # type: ignore[override]
        raise RuntimeError("environment mutated during iteration")

    def copy(self):
        return dict(self)


def test_normalize_expands_variables_strips_quotes_and_lowercases(monkeypatch) -> None:
    monkeypatch.setenv("PLAYTRACE_GAMES", r"C:\Games")

    normalized = PathNormalizer().normalize('"%PLAYTRACE_GAMES%/MyGame/Launcher.EXE"')

    assert normalized == r"c:\games\mygame\launcher.exe"


def test_normalize_converts_relative_paths_to_absolute_paths(tmp_path: Path, monkeypatch) -> None:
    games_root = tmp_path / "Games"
    games_root.mkdir()
    monkeypatch.chdir(tmp_path)

    normalized = PathNormalizer().normalize(r"Games\MyGame.exe")

    assert normalized == str(PureWindowsPath(games_root / "MyGame.exe")).lower()


def test_normalize_returns_none_for_empty_values() -> None:
    normalizer = PathNormalizer()

    assert normalizer.normalize(None) is None
    assert normalizer.normalize("   ") is None


def test_normalize_expands_windows_style_variables_even_without_host_support(monkeypatch) -> None:
    monkeypatch.setenv("PLAYTRACE_GAMES", r"C:\Games")
    monkeypatch.setattr(os.path, "expandvars", lambda value: value)

    normalized = PathNormalizer().normalize(r"%PLAYTRACE_GAMES%\MyGame\Launcher.EXE")

    assert normalized == r"c:\games\mygame\launcher.exe"


def test_normalize_expands_windows_style_variables_case_insensitively(monkeypatch) -> None:
    monkeypatch.setattr(pathing_module.os, "environ", {"ProgramFiles": r"C:\Program Files"})
    monkeypatch.setattr(pathing_module.os.path, "expandvars", lambda value: value)

    normalized = PathNormalizer().normalize(r"%PROGRAMFILES%\Steam\Steam.exe")

    assert normalized == r"c:\program files\steam\steam.exe"


def test_normalize_preserves_unknown_windows_style_variables(monkeypatch) -> None:
    monkeypatch.setattr(pathing_module.os, "environ", {"ProgramFiles": r"C:\Program Files"})
    monkeypatch.setattr(pathing_module.os.path, "expandvars", lambda value: value)

    normalized = PathNormalizer().normalize(r"%DOES_NOT_EXIST%\Steam\Steam.exe")

    assert normalized == r"%does_not_exist%\steam\steam.exe"


def test_normalize_uses_environment_snapshot_for_case_insensitive_expansion(monkeypatch) -> None:
    monkeypatch.setattr(
        pathing_module.os,
        "environ",
        UnstableItemsEnviron({"ProgramFiles": r"C:\Program Files"}),
    )
    monkeypatch.setattr(pathing_module.os.path, "expandvars", lambda value: value)

    normalized = PathNormalizer().normalize(r"%PROGRAMFILES%\Steam\Steam.exe")

    assert normalized == r"c:\program files\steam\steam.exe"
