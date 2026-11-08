from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

import playtrace.normalize.pathing as pathing_module
from playtrace.normalize.pathing import PathNormalizer


@given(st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=90), min_size=1))
def test_path_normalizer_lowercases_windows_paths(name: str) -> None:
    path = rf"C:\Games\{name}\GAME.EXE"

    assert PathNormalizer().normalize(path) == rf"c:\games\{name.lower()}\game.exe"


@given(st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=90), min_size=1))
def test_path_normalizer_converts_forward_slashes_to_backslashes(name: str) -> None:
    path = f"C:/Games/{name}/GAME.EXE"

    assert PathNormalizer().normalize(path) == rf"c:\games\{name.lower()}\game.exe"


@given(st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=90), min_size=1))
def test_path_normalizer_strips_surrounding_quotes(name: str) -> None:
    path = rf'"C:\Games\{name}\GAME.EXE"'

    assert PathNormalizer().normalize(path) == rf"c:\games\{name.lower()}\game.exe"


def test_path_normalizer_expands_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")

    assert (
        PathNormalizer().normalize(r"%ProgramFiles%\Steam\Steam.exe")
        == r"c:\program files\steam\steam.exe"
    )


def test_path_normalizer_expands_environment_variables_case_insensitively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pathing_module.os, "environ", {"ProgramFiles": r"C:\Program Files"})

    assert (
        PathNormalizer().normalize(r"%PROGRAMFILES%\Steam\Steam.exe")
        == r"c:\program files\steam\steam.exe"
    )


def test_path_normalizer_resolves_relative_paths_to_absolute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pin the working directory to a Windows path so the test is host-independent.
    monkeypatch.setattr(pathing_module.os, "getcwd", lambda: r"D:\Work\Library")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"d:\work\library\games\balatro.exe"


def test_path_normalizer_leaves_relative_paths_unanchored_without_windows_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A POSIX working directory has no drive, so it cannot anchor a Windows path.
    monkeypatch.setattr(pathing_module.os, "getcwd", lambda: "/home/analyst")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"games\balatro.exe"


def test_path_normalizer_does_not_depend_on_host_os_path_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pathing_module.os, "getcwd", lambda: r"D:\Work\Library")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setattr(pathing_module.os.path, "expandvars", lambda value: value)
    monkeypatch.setattr(pathing_module.os.path, "abspath", lambda value: f"/workspace/{value}")

    normalizer = PathNormalizer()

    assert normalizer.normalize(r"%ProgramFiles%\Steam\Steam.exe") == r"c:\program files\steam\steam.exe"
    assert normalizer.normalize(r"Games\Balatro.exe") == r"d:\work\library\games\balatro.exe"


def test_path_normalizer_returns_none_for_none_or_empty() -> None:
    normalizer = PathNormalizer()

    assert normalizer.normalize(None) is None
    assert normalizer.normalize("") is None
    assert normalizer.normalize("   ") is None


@given(
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=1,
        max_size=12,
    )
)
def test_path_normalizer_is_idempotent(name: str) -> None:
    original = rf'"C:/Games/{name}/GAME.EXE"'
    normalizer = PathNormalizer()

    once = normalizer.normalize(original)
    assert once is not None
    assert normalizer.normalize(once) == once
