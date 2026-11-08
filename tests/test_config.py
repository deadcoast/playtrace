from __future__ import annotations

import json
import string
import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from playtrace.config.loader import ConfigLoader
from playtrace.config.models import ConfigModel
from playtrace.models.enums import SourceName

VALID_SOURCES = [source.value for source in SourceName]
ASCII_ALPHABET = string.ascii_letters + string.digits + "_"


def _override_path(name: str) -> str:
    return rf"C:\Games\{name}\game.exe"


def _render_toml(
    merge_window: int = 2,
    default_sources: list[str] | None = None,
    overrides: dict[str, str] | None = None,
) -> str:
    default_sources = default_sources or []
    overrides = overrides or {}
    sources_text = ", ".join(json.dumps(source) for source in default_sources)
    overrides_text = ", ".join(
        f"{json.dumps(key)} = {json.dumps(value)}" for key, value in overrides.items()
    )
    return (
        "[session]\n"
        f"merge_dedupe_window_minutes = {merge_window}\n\n"
        "[sources]\n"
        f"default = [{sources_text}]\n\n"
        "[classification]\n"
        f"overrides = {{ {overrides_text} }}\n"
    )


def test_config_model_exposes_pascal_case_public_name() -> None:
    assert ConfigModel is ConfigModel


@given(st.integers(max_value=0))
def test_config_model_rejects_non_positive_merge_windows(value: int) -> None:
    with pytest.raises(ValueError, match="session_merge_dedupe_window_minutes"):
        ConfigModel(session_merge_dedupe_window_minutes=value)


@given(
    st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=20).filter(
        lambda value: value not in VALID_SOURCES
    )
)
def test_config_model_rejects_invalid_source_names(value: str) -> None:
    with pytest.raises(ValueError, match="default_sources"):
        ConfigModel(default_sources=[value])


@given(st.one_of(st.text(), st.floats(allow_nan=False), st.booleans()))
def test_config_model_rejects_invalid_field_types(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ConfigModel(session_merge_dedupe_window_minutes=value)  # type: ignore[arg-type]


@given(
    st.integers(min_value=1, max_value=180),
        st.lists(st.sampled_from(VALID_SOURCES), unique=True, max_size=len(VALID_SOURCES)),
        st.dictionaries(
        st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=12).map(_override_path),
        st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=12),
        max_size=4,
    ),
)
def test_config_loader_parses_valid_toml(
    merge_window: int,
    default_sources: list[str],
    overrides: dict[str, str],
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "playtrace.toml"
        path.write_text(
            _render_toml(
                merge_window=merge_window,
                default_sources=default_sources,
                overrides=overrides,
            ),
            encoding="utf-8",
        )

        assert ConfigLoader().load(path) == ConfigModel(
            session_merge_dedupe_window_minutes=merge_window,
            default_sources=default_sources,
            classification_overrides=overrides,
        )


@given(
    st.sampled_from(
        [
            "[session\nmerge_dedupe_window_minutes = 2\n",
            "[sources]\ndefault = [\n",
            "[classification]\noverrides = { \"a\" = \n",
        ]
    )
)
def test_config_loader_raises_for_invalid_toml(content: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "invalid.toml"
        path.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid TOML"):
            ConfigLoader().load(path)


@given(
    st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=12)
)
def test_config_loader_ignores_unknown_fields(name: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "playtrace.toml"
        path.write_text(
            _render_toml() + f"\n[unknown]\n{name} = {json.dumps(name)}\n",
            encoding="utf-8",
        )

        assert ConfigLoader().load(path) == ConfigModel()


@given(st.integers(min_value=1, max_value=180))
def test_config_loader_applies_defaults_for_missing_optional_fields(merge_window: int) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "minimal.toml"
        path.write_text(
            "[session]\n"
            f"merge_dedupe_window_minutes = {merge_window}\n",
            encoding="utf-8",
        )

        assert ConfigLoader().load(path) == ConfigModel(
            session_merge_dedupe_window_minutes=merge_window
        )


@given(
    st.integers(min_value=1, max_value=180),
        st.lists(st.sampled_from(VALID_SOURCES), unique=True, max_size=len(VALID_SOURCES)),
        st.dictionaries(
        st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=12).map(_override_path),
        st.text(alphabet=ASCII_ALPHABET, min_size=1, max_size=12),
        max_size=4,
    ),
)
def test_config_loader_round_trip_preserves_config(
    merge_window: int,
    default_sources: list[str],
    overrides: dict[str, str],
) -> None:
    config = ConfigModel(
        session_merge_dedupe_window_minutes=merge_window,
        default_sources=default_sources,
        classification_overrides=overrides,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "roundtrip.toml"
        path.write_text(
            _render_toml(
                merge_window=config.session_merge_dedupe_window_minutes,
                default_sources=config.default_sources,
                overrides=config.classification_overrides,
            ),
            encoding="utf-8",
        )

        assert ConfigLoader().load(path) == config


def test_config_loader_returns_default_config_for_missing_path() -> None:
    assert ConfigLoader().load(Path("missing-playtrace.toml")) == ConfigModel()


def test_config_loader_loads_minimal_toml_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "playtrace.toml"
    path.write_text("[sources]\ndefault = [\"security_log\"]\n", encoding="utf-8")

    assert ConfigLoader().load(path) == ConfigModel(default_sources=["security_log"])


def test_config_loader_loads_full_toml(tmp_path: Path) -> None:
    path = tmp_path / "playtrace.toml"
    path.write_text(
        _render_toml(
            merge_window=5,
            default_sources=["security_log", "prefetch"],
            overrides={r"C:\Games\Balatro\balatro.exe": "game"},
        ),
        encoding="utf-8",
    )

    assert ConfigLoader().load(path) == ConfigModel(
        session_merge_dedupe_window_minutes=5,
        default_sources=["security_log", "prefetch"],
        classification_overrides={r"C:\Games\Balatro\balatro.exe": "game"},
    )
