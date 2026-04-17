from __future__ import annotations

from pathlib import Path, PureWindowsPath

from playtrace.normalize.pathing import PathNormalizer


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
