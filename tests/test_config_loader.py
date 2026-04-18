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


def test_load_parses_defaults_command_blocks_and_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
[defaults]
active_profile = "ready"
theme = "midnight"

[scan]
full = true

[profiles.ready.report]
limit = 5
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.active_profile == "ready"
    assert config.scan.full is True
    assert config.me.refresh is False
    assert config.report.limit is not None
    assert config.doctor.severity is not None
    assert config.titles.limit is not None
    assert config.sessions.days is not None
    assert config.inspect is not None
    assert config.sources is not None
    assert config.map is not None
    assert config.export is not None
    assert config.profiles["ready"].report.limit == 5


def test_load_parses_export_scope(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
[export]
format = "json"
scope = "lineage"
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.export.scope == "lineage"


def test_load_ignores_unknown_fields_in_nested_config(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
[defaults]
theme = "midnight"
unknown_default = 123

[report]
limit = 10
unknown_report_field = "ignored"
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.theme == "midnight"
    assert config.report.limit == 10


def test_load_ignores_unknown_top_level_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
future_option = "ignored"

[future_table]
enabled = true

[defaults]
theme = "midnight"
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.theme == "midnight"


def test_load_preserves_current_nested_config_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
[session]
merge_dedupe_window_minutes = 5

[sources]
default = ["security_log"]

[classification]
overrides = { "C:\\\\Games\\\\Legacy.exe" = "game" }
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.reconstruction.session_merge_dedupe_window_minutes == 5
    assert config.defaults.default_sources == ["security_log"]
    assert config.defaults.classification.overrides[r"C:\Games\Legacy.exe"] == "game"


def test_load_preserves_legacy_flat_key_shape_if_still_supported(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
session_merge_dedupe_window_minutes = 5
default_sources = ["security_log"]
classification_overrides = { "C:\\\\Games\\\\Legacy.exe" = "game" }
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.reconstruction.session_merge_dedupe_window_minutes == 5
    assert config.defaults.default_sources == ["security_log"]
    assert config.defaults.classification.overrides[r"C:\Games\Legacy.exe"] == "game"


def test_load_prefers_new_nested_shape_when_legacy_flat_keys_are_also_present(tmp_path: Path) -> None:
    config_path = tmp_path / "playtrace.toml"
    config_path.write_text(
        """
session_merge_dedupe_window_minutes = 5
default_sources = ["security_log"]
classification_overrides = { "C:\\\\Games\\\\Legacy.exe" = "game" }

[defaults]
default_sources = ["userassist"]

[defaults.reconstruction]
session_merge_dedupe_window_minutes = 2

[defaults.classification]
overrides = { "C:\\\\Games\\\\Legacy.exe" = "launcher" }

[report]
limit = 3
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader().load(config_path)

    assert config.defaults.reconstruction.session_merge_dedupe_window_minutes == 2
    assert config.defaults.default_sources == ["userassist"]
    assert config.defaults.classification.overrides[r"C:\Games\Legacy.exe"] == "launcher"
    assert config.report.limit == 3
