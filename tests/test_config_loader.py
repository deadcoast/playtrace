from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from playtrace.config.loader import ConfigLoader
from playtrace.config.models import ConfigModel


def test_config_model_validates_positive_merge_window() -> None:
    with pytest.raises(ValueError, match="positive"):
        ConfigModel(session_merge_dedupe_window_minutes=0)


def test_config_model_validates_source_names() -> None:
    with pytest.raises(ValueError, match="default_sources"):
        ConfigModel(default_sources=["not-a-source"])


def test_load_returns_defaults_for_missing_file(tmp_path: Path) -> None:
    config = ConfigLoader().load(tmp_path / "missing.toml")

    assert config == ConfigModel()


def test_load_parses_documented_toml_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
[session]
merge_dedupe_window_minutes = 5

[sources]
default = ["security_log", "prefetch"]

[classification]
overrides = { "C:\\\\Games\\\\MyGame.exe" = "game" }
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.session_merge_dedupe_window_minutes == 5
    assert config.default_sources == ["security_log", "prefetch"]
    assert config.classification_overrides == {r"C:\Games\MyGame.exe": "game"}


def test_load_ignores_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
answer = 42

[session]
merge_dedupe_window_minutes = 4
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config == ConfigModel(session_merge_dedupe_window_minutes=4)


def test_load_raises_for_invalid_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.toml"
    config_path.write_text("[session\nmerge_dedupe_window_minutes = 4", encoding="utf-8")

    with pytest.raises(tomllib.TOMLDecodeError):
        ConfigLoader().load(config_path)
