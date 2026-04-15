from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


def test_path_normalizer_resolves_relative_paths_to_absolute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(r"C:\Users\ryanf")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"c:\users\ryanf\games\balatro.exe"


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
