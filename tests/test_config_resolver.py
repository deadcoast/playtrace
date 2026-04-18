from __future__ import annotations

import pytest

from playtrace.config.models import ConfigModel, ProfileConfig
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import (
    RawDoctorInput,
    RawExportInput,
    RawInspectInput,
    RawMapInput,
    RawMeInput,
    RawReportInput,
    RawScanInput,
    RawSessionsInput,
    RawSourcesInput,
    RawTitlesInput,
)


@pytest.fixture
def config() -> ConfigModel:
    return ConfigModel(profiles={"ready": ProfileConfig()})


def test_resolver_applies_cli_over_command_over_profile_over_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.theme = "midnight"
    config.profiles["ready"].scan.theme = "amber"
    config.scan.theme = "ice"

    resolved = ConfigResolver().resolve_scan(
        config=config,
        cli=RawScanInput(theme="mono"),
        spec_name=None,
    )

    assert resolved.presentation.theme == "mono"


def test_resolver_uses_ready_profile_when_no_profile_is_requested(
    config: ConfigModel,
) -> None:
    config.defaults.active_profile = None

    resolved = ConfigResolver().resolve_report(
        config=config,
        cli=RawReportInput(),
        spec_name=None,
    )

    assert resolved.profile_name == "ready"


def test_resolver_falls_back_to_built_in_ready_when_active_profile_is_missing(
    config: ConfigModel,
) -> None:
    config.defaults.active_profile = "missing"

    resolved = ConfigResolver().resolve_me(
        config=config,
        cli=RawMeInput(),
        spec_name=None,
    )

    assert resolved.profile_name == "ready"


def test_resolver_applies_command_block_over_shared_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.theme = "midnight"
    config.report.theme = "amber"

    resolved = ConfigResolver().resolve_report(
        config=config,
        cli=RawReportInput(),
        spec_name=None,
    )

    assert resolved.presentation.theme == "amber"


@pytest.mark.parametrize(
    ("resolver_name", "command_setter", "expected"),
    [
        ("resolve_scan", lambda config: setattr(config.scan, "theme", "amber"), "amber"),
        ("resolve_me", lambda config: setattr(config.me, "theme", "amber"), "amber"),
        ("resolve_doctor", lambda config: setattr(config.doctor, "theme", "amber"), "amber"),
        ("resolve_titles", lambda config: setattr(config.titles, "theme", "amber"), "amber"),
        ("resolve_sessions", lambda config: setattr(config.sessions, "theme", "amber"), "amber"),
        ("resolve_inspect", lambda config: setattr(config.inspect, "theme", "amber"), "amber"),
        ("resolve_sources", lambda config: setattr(config.sources, "theme", "amber"), "amber"),
        ("resolve_map", lambda config: setattr(config.map, "theme", "amber"), "amber"),
        ("resolve_export", lambda config: setattr(config.export, "theme", "amber"), "amber"),
    ],
)
def test_resolver_applies_command_blocks_across_public_commands(
    config: ConfigModel,
    resolver_name: str,
    command_setter,
    expected: str,
) -> None:
    config.defaults.theme = "midnight"
    command_setter(config)

    resolved = getattr(ConfigResolver(), resolver_name)(
        config=config,
        cli=build_empty_cli_input(resolver_name),
        spec_name=None,
    )

    assert resolved.presentation.theme == expected


def test_resolver_applies_titles_limit_over_shared_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.titles.limit = 50
    config.titles.limit = 5

    resolved = ConfigResolver().resolve_titles(
        config=config,
        cli=RawTitlesInput(),
        spec_name=None,
    )

    assert resolved.limit == 5


def test_resolver_applies_sessions_days_over_shared_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.sessions.days = 30
    config.sessions.days = 7

    resolved = ConfigResolver().resolve_sessions(
        config=config,
        cli=RawSessionsInput(),
        spec_name=None,
    )

    assert resolved.days == 7


def test_resolver_applies_map_auto_over_shared_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.map.auto = False
    config.map.auto = True

    resolved = ConfigResolver().resolve_map(
        config=config,
        cli=RawMapInput(),
        spec_name=None,
    )

    assert resolved.auto is True


def test_resolver_applies_titles_cli_over_command_over_profile_over_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.titles.limit = 50
    config.profiles["ready"].titles.limit = 10
    config.titles.limit = 5

    resolved = ConfigResolver().resolve_titles(
        config=config,
        cli=RawTitlesInput(limit=2),
        spec_name=None,
    )

    assert resolved.limit == 2


def test_resolver_applies_sessions_cli_over_command_over_profile_over_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.sessions.days = 30
    config.profiles["ready"].sessions.days = 14
    config.sessions.days = 7

    resolved = ConfigResolver().resolve_sessions(
        config=config,
        cli=RawSessionsInput(days=3),
        spec_name=None,
    )

    assert resolved.days == 3


def test_resolver_applies_map_cli_over_command_over_profile_over_defaults(
    config: ConfigModel,
) -> None:
    config.defaults.map.auto = False
    config.profiles["ready"].map.auto = False
    config.map.auto = False

    resolved = ConfigResolver().resolve_map(
        config=config,
        cli=RawMapInput(auto=True),
        spec_name=None,
    )

    assert resolved.auto is True


def build_empty_cli_input(resolver_name: str):
    if resolver_name == "resolve_scan":
        return RawScanInput()
    if resolver_name == "resolve_me":
        return RawMeInput()
    if resolver_name == "resolve_doctor":
        return RawDoctorInput()
    if resolver_name == "resolve_titles":
        return RawTitlesInput()
    if resolver_name == "resolve_sessions":
        return RawSessionsInput()
    if resolver_name == "resolve_inspect":
        return RawInspectInput()
    if resolver_name == "resolve_sources":
        return RawSourcesInput()
    if resolver_name == "resolve_map":
        return RawMapInput()
    if resolver_name == "resolve_export":
        return RawExportInput()
    return RawReportInput()
