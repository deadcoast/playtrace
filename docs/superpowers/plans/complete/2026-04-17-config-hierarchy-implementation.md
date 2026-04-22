# Playtrace Config Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Playtrace configuration into the real default-behavior layer by implementing shared defaults, per-command blocks, optional power-user profiles, a shared resolver, and end-to-end command integration with CLI-over-config precedence.

**Architecture:** Expand the existing config schema into nested user-facing defaults and command blocks, then add a runtime resolution layer that converts built-in defaults, config state, optional profile selection, and raw CLI inputs into typed resolved settings per command. Feed reconstruction-affecting settings through the truth layer and renderer-affecting settings through command-specific presentation settings so the CLI stays truthful while becoming fully configurable by default.

**Tech Stack:** Python 3.12, Typer, Rich, SQLite, pytest, existing `playtrace/config`, `playtrace/services`, `playtrace/store`, `playtrace/merge`, and CLI modules

---

## File Structure

### New Files

- `playtrace/config/resolver.py`
  - Shared precedence engine that merges built-in defaults, loaded config, optional profile choice, command block overrides, and raw CLI inputs into resolved settings.
- `playtrace/config/runtime.py`
  - Runtime dataclasses for raw CLI inputs, command names, unset-aware values, reconstruction settings, presentation settings, and per-command resolved settings.
- `tests/test_config_resolver.py`
  - Precedence tests for built-in defaults -> config defaults -> active profile -> per-command block -> CLI.
- `tests/test_command_config_integration.py`
  - Service and CLI integration tests proving config-backed defaults are actually consumed by commands and overridden by explicit CLI input.
- `docs/config.example.toml`
  - Human-readable example config showing `[defaults]`, per-command blocks, and the implicit `ready` profile.

### Modified Files

- `playtrace/config/models.py`
  - Expand the user-facing config model beyond the current three fields into nested defaults, command blocks, and profiles.
- `playtrace/config/loader.py`
  - Parse the expanded TOML shape into the new config model while preserving compatibility behavior for unknown fields.
- `playtrace/cli/common.py`
  - Add shared config/spec option helpers and any unset-aware CLI helpers needed by command handlers.
- `playtrace/cli/cmd_scan.py`
  - Stop hardcoding parser defaults as user intent; pass raw input plus config/spec selection.
- `playtrace/cli/cmd_me.py`
  - Add `--config`, optional `--spec`, unset-aware theme/refresh handling, and resolved settings handoff.
- `playtrace/cli/cmd_report.py`
  - Route through the resolver and stop masking config with parser defaults.
- `playtrace/cli/cmd_doctor.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_titles.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_sessions.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_inspect.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_sources.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_map.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/cli/cmd_export.py`
  - Add config/spec support and resolved settings handoff.
- `playtrace/services/scanner.py`
  - Consume resolved scan settings and pass reconstruction settings into the rebuild path.
- `playtrace/services/dashboard.py`
  - Consume resolved `me` settings and share refresh/config behavior with `scan`.
- `playtrace/services/reporter.py`
  - Consume resolved report/titles/sessions settings instead of hardcoded request defaults.
- `playtrace/services/doctor.py`
  - Consume resolved doctor settings and surface config-driven thresholds/presentation.
- `playtrace/services/audit.py`
  - Accept config-driven severity thresholds and section visibility for doctor/report/dashboard use.
- `playtrace/services/inspector.py`
  - Consume resolved inspect settings for output depth and normalization defaults.
- `playtrace/services/sources.py`
  - Consume resolved sources settings for output depth and normalization defaults.
- `playtrace/services/mapper.py`
  - Consume resolved map settings for auto-merge posture and classification defaults.
- `playtrace/services/exporter.py`
  - Consume resolved export settings for format and scope defaults.
- `playtrace/store/db.py`
  - Accept reconstruction settings during rebuild and expose any config-backed query semantics needed by resolved settings.
- `playtrace/merge/sessions.py`
  - Accept configured session merge behavior from resolved reconstruction settings.
- `playtrace/classify/resolver.py`
  - Accept config-driven classification overrides as default mapping policy with the approved precedence.
- `tests/test_config_loader.py`
  - Expand model/loader coverage to the new nested config shape.
- `tests/test_dashboard_service.py`
  - Cover `me` config resolution and refresh precedence.
- `tests/test_audit_service.py`
  - Cover doctor threshold and visibility defaults.
- `tests/test_report_render.py`
  - Cover report/titles/sessions config-backed defaults and CLI overrides.
- `tests/test_sources_command.py`
  - Cover sources config-backed defaults.
- `tests/test_inspect_view.py`
  - Cover inspect config-backed defaults.
- `tests/test_export_service.py`
  - Cover export config-backed defaults.
- `tests/test_title_resolution.py`
  - Cover classification override precedence.
- `tests/test_store_schema.py`
  - Cover rebuild behavior with configured reconstruction settings.
- `docs/VALTEST.md`
  - Add config-specific hands-on validation results after implementation.

### Existing Files to Read During Implementation

- `docs/superpowers/specs/2026-04-17-config-hierarchy-design.md`
- `playtrace/config/models.py`
- `playtrace/config/loader.py`
- `playtrace/cli/common.py`
- `playtrace/services/scanner.py`
- `playtrace/services/dashboard.py`
- `playtrace/services/reporter.py`
- `playtrace/services/doctor.py`
- `playtrace/services/audit.py`
- `playtrace/store/db.py`
- `playtrace/merge/sessions.py`
- `playtrace/classify/resolver.py`

## Task 1: Expand the Config Schema, Loader, and Example Config

**Files:**
- Create: `docs/config.example.toml`
- Modify: `playtrace/config/models.py`
- Modify: `playtrace/config/loader.py`
- Test: `tests/test_config_loader.py`

- [ ] **Step 1: Write the failing tests for the expanded nested config shape**

```python
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
```

- [ ] **Step 2: Run the loader tests to verify the current flat model fails**

Run: `uv run pytest tests/test_config_loader.py -q`
Expected: FAIL because `ConfigModel` and `ConfigLoader` only understand the old flat fields and cannot bridge the current nested config shape into the new hierarchy while preserving compatibility.

- [ ] **Step 3: Implement the nested config model, loader mapping, current-shape compatibility, optional flat-key compatibility if already shipped, and example config**

```python
@dataclass(slots=True)
class DefaultsConfig:
    active_profile: str = "ready"
    theme: str | None = None
    density: str | None = None
    default_sources: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommandConfig:
    theme: str | None = None
    density: str | None = None


@dataclass(slots=True)
class ConfigModel:
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    me: MeConfig = field(default_factory=MeConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    doctor: DoctorConfig = field(default_factory=DoctorConfig)
    titles: TitlesConfig = field(default_factory=TitlesConfig)
    sessions: SessionsConfig = field(default_factory=SessionsConfig)
    inspect: InspectConfig = field(default_factory=InspectConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    map: MapConfig = field(default_factory=MapConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)


class ConfigLoader:
    def _apply_compatibility_bridges(self, data: dict[str, Any]) -> dict[str, Any]:
        ...
```

- [ ] **Step 4: Re-run the loader tests and inspect the example config**

Run: `uv run pytest tests/test_config_loader.py -q`
Expected: PASS with nested config parsing and validation.

- [ ] **Step 5: Commit the expanded config schema**

```bash
git add docs/config.example.toml playtrace/config/models.py playtrace/config/loader.py tests/test_config_loader.py
git commit -m "Expand Playtrace config schema"
```

## Task 2: Add the Shared Runtime Resolver and Unset-Aware CLI Input Models

**Files:**
- Create: `playtrace/config/runtime.py`
- Create: `playtrace/config/resolver.py`
- Create: `tests/test_config_resolver.py`

- [ ] **Step 1: Write the failing resolver precedence tests**

```python
def test_resolver_applies_cli_over_command_over_profile_over_defaults() -> None:
    resolved = ConfigResolver().resolve_scan(
        config=config,
        cli=RawScanInput(theme="mono", theme_set=True),
        spec_name=None,
    )
    assert resolved.presentation.theme == "mono"


def test_resolver_uses_ready_profile_when_no_profile_is_requested() -> None:
    config.defaults.active_profile = None
    resolved = ConfigResolver().resolve_report(config=config, cli=RawReportInput(), spec_name=None)
    assert resolved.profile_name == "ready"


def test_resolver_falls_back_to_built_in_ready_when_active_profile_is_missing() -> None:
    config.defaults.active_profile = "missing"
    resolved = ConfigResolver().resolve_me(config=config, cli=RawMeInput(), spec_name=None)
    assert resolved.profile_name == "ready"


def test_resolver_applies_command_block_over_shared_defaults() -> None:
    config.defaults.theme = "midnight"
    config.report.theme = "amber"
    resolved = ConfigResolver().resolve_report(config=config, cli=RawReportInput(), spec_name=None)
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
def test_resolver_applies_command_blocks_across_public_commands(resolver_name, command_setter, expected) -> None:
    config.defaults.theme = "midnight"
    command_setter(config)
    resolved = getattr(ConfigResolver(), resolver_name)(config=config, cli=build_empty_cli_input(resolver_name), spec_name=None)
    assert resolved.presentation.theme == expected


def test_resolver_applies_titles_limit_over_shared_defaults() -> None:
    config.defaults.titles.limit = 50
    config.titles.limit = 5
    resolved = ConfigResolver().resolve_titles(config=config, cli=RawTitlesInput(), spec_name=None)
    assert resolved.limit == 5


def test_resolver_applies_sessions_days_over_shared_defaults() -> None:
    config.defaults.sessions.days = 30
    config.sessions.days = 7
    resolved = ConfigResolver().resolve_sessions(config=config, cli=RawSessionsInput(), spec_name=None)
    assert resolved.days == 7


def test_resolver_applies_map_auto_over_shared_defaults() -> None:
    config.defaults.map.auto = False
    config.map.auto = True
    resolved = ConfigResolver().resolve_map(config=config, cli=RawMapInput(), spec_name=None)
    assert resolved.auto is True


def test_resolver_applies_titles_cli_over_command_over_profile_over_defaults() -> None:
    config.defaults.titles.limit = 50
    config.profiles["ready"].titles.limit = 10
    config.titles.limit = 5
    resolved = ConfigResolver().resolve_titles(config=config, cli=RawTitlesInput(limit=2), spec_name=None)
    assert resolved.limit == 2


def test_resolver_applies_sessions_cli_over_command_over_profile_over_defaults() -> None:
    config.defaults.sessions.days = 30
    config.profiles["ready"].sessions.days = 14
    config.sessions.days = 7
    resolved = ConfigResolver().resolve_sessions(config=config, cli=RawSessionsInput(days=3), spec_name=None)
    assert resolved.days == 3


def test_resolver_applies_map_cli_over_command_over_profile_over_defaults() -> None:
    config.defaults.map.auto = False
    config.profiles["ready"].map.auto = False
    config.map.auto = False
    resolved = ConfigResolver().resolve_map(config=config, cli=RawMapInput(auto=True), spec_name=None)
    assert resolved.auto is True
```

- [ ] **Step 2: Run the resolver tests and confirm the runtime layer does not exist yet**

Run: `uv run pytest tests/test_config_resolver.py -q`
Expected: FAIL because there is no resolver or unset-aware runtime model.

- [ ] **Step 3: Implement runtime dataclasses and the shared resolver**

```python
UNSET = object()


@dataclass(slots=True)
class RawScanInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    sources: list[str] | object = UNSET


class ConfigResolver:
    def resolve_scan(self, config: ConfigModel, cli: RawScanInput, spec_name: str | None) -> ResolvedScanSettings:
        ...
```

- [ ] **Step 4: Re-run the resolver tests**

Run: `uv run pytest tests/test_config_resolver.py -q`
Expected: PASS with the approved precedence chain enforced.

- [ ] **Step 5: Commit the resolver layer**

```bash
git add playtrace/config/runtime.py playtrace/config/resolver.py tests/test_config_resolver.py
git commit -m "Add config resolver and runtime settings"
```

## Task 3: Rework Shared CLI Options and Primary Commands to Use Resolved Settings

**Files:**
- Modify: `playtrace/cli/common.py`
- Modify: `playtrace/cli/cmd_scan.py`
- Modify: `playtrace/cli/cmd_me.py`
- Modify: `playtrace/cli/cmd_report.py`
- Modify: `playtrace/cli/cmd_doctor.py`
- Modify: `playtrace/services/scanner.py`
- Modify: `playtrace/services/dashboard.py`
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/services/doctor.py`
- Create: `tests/test_command_config_integration.py`
- Modify: `tests/test_dashboard_service.py`
- Modify: `tests/test_audit_service.py`
- Modify: `tests/test_report_render.py`

- [ ] **Step 1: Write the failing integration tests for primary command precedence**

```python
def test_scan_uses_config_default_sources_when_cli_sources_are_unset(tmp_path: Path) -> None:
    snapshot = ScannerService().run_for_snapshot(
        ScanRequest(db_path=tmp_path / "playtrace.db", config_path=config_path, raw=RawScanInput())
    )
    assert snapshot.selected_sources == ["userassist"]


def test_report_cli_theme_overrides_config_theme(tmp_path: Path, capsys) -> None:
    ReporterService().render_default(
        ReportRequest(db_path=tmp_path / "playtrace.db", config_path=config_path, raw=RawReportInput(theme="mono"))
    )
    assert "playtrace REPORT" in capsys.readouterr().out
```

- [ ] **Step 2: Run the primary integration tests to verify the current request/service layer ignores config**

Run: `uv run pytest tests/test_command_config_integration.py tests/test_dashboard_service.py tests/test_audit_service.py tests/test_report_render.py -q`
Expected: FAIL because the commands and services still use parser defaults and do not resolve config.

- [ ] **Step 3: Implement shared CLI options, raw input capture, and resolved-settings handoff**

```python
SpecOption = Annotated[str | None, typer.Option("--spec", help="Optional power-user profile name.")]


@app.command("scan")
def scan(...):
    raw = RawScanInput(theme=theme, density=density, sources=sources, ...)
    ScannerService().render(ScanRequest(db_path=db, config_path=config, spec_name=spec, raw=raw))
```

- [ ] **Step 4: Re-run the primary integration tests**

Run: `uv run pytest tests/test_command_config_integration.py tests/test_dashboard_service.py tests/test_audit_service.py tests/test_report_render.py -q`
Expected: PASS with config-backed defaults and CLI-over-config precedence on `scan`, `me`, `report`, and `doctor`.

- [ ] **Step 5: Commit primary command config integration**

```bash
git add playtrace/cli/common.py playtrace/cli/cmd_scan.py playtrace/cli/cmd_me.py playtrace/cli/cmd_report.py playtrace/cli/cmd_doctor.py playtrace/services/scanner.py playtrace/services/dashboard.py playtrace/services/reporter.py playtrace/services/doctor.py tests/test_command_config_integration.py tests/test_dashboard_service.py tests/test_audit_service.py tests/test_report_render.py
git commit -m "Resolve config for primary commands"
```

## Task 4: Feed Reconstruction Settings Through the Truth Layer

**Files:**
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/merge/sessions.py`
- Modify: `playtrace/classify/resolver.py`
- Modify: `playtrace/services/scanner.py`
- Modify: `tests/test_store_schema.py`
- Modify: `tests/test_title_resolution.py`

- [ ] **Step 1: Write the failing tests for config-driven reconstruction behavior**

```python
def test_rebuild_uses_configured_session_merge_window(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    seed_session_merge_edge_case(db)
    db.rebuild_from_artifacts_and_mappings()
    baseline_sessions = db.count_sessions()
    db.rebuild_from_artifacts_and_mappings(settings=ReconstructionSettings(session_merge_dedupe_window_minutes=10))
    assert baseline_sessions == 2
    assert db.count_sessions() == 1


def test_title_resolution_applies_config_classification_overrides_below_user_mappings() -> None:
    result = TitleResolver().resolve(executables, sessions, mappings=user_mappings, config_overrides={"C:\\Game.exe": "game"})
    assert result.titles[0].classification is Classification.GAME


def test_rebuild_uses_configured_duplicate_auto_merge(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    seed_duplicate_evidence(db)
    db.rebuild_from_artifacts_and_mappings()
    baseline_duplicate_groups = db.count_duplicate_title_groups()
    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(
            duplicate_auto_merge=True,
        )
    )
    assert baseline_duplicate_groups == 1
    assert db.count_duplicate_title_groups() == 0


def test_rebuild_uses_configured_duplicate_similarity_threshold(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    seed_borderline_duplicate_evidence(db)
    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(
            duplicate_auto_merge=True,
            duplicate_similarity_threshold=0.95,
        )
    )
    strict_duplicate_groups = db.count_duplicate_title_groups()
    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(
            duplicate_auto_merge=True,
            duplicate_similarity_threshold=0.75,
        )
    )
    assert strict_duplicate_groups == 1
    assert db.count_duplicate_title_groups() == 0


def test_rebuild_uses_configured_minimum_evidence_confidence(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    seed_low_confidence_evidence(db)
    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(minimum_evidence_confidence="low")
    )
    low_threshold_titles = db.load_snapshot(limit=10).coverage.tracked_titles
    db.rebuild_from_artifacts_and_mappings(
        settings=ReconstructionSettings(minimum_evidence_confidence="medium")
    )
    assert low_threshold_titles == 1
    assert db.load_snapshot(limit=10).coverage.tracked_titles == 0
```

- [ ] **Step 2: Run the reconstruction tests and confirm the rebuild path cannot accept settings yet**

Run: `uv run pytest tests/test_store_schema.py tests/test_title_resolution.py -q`
Expected: FAIL because rebuild and title resolution are not config-driven.

- [ ] **Step 3: Implement reconstruction settings plumbing**

```python
@dataclass(slots=True)
class ReconstructionSettings:
    session_merge_dedupe_window_minutes: int = 2
    duplicate_auto_merge: bool = False
    duplicate_similarity_threshold: float = 0.85
    minimum_evidence_confidence: str = "low"
    classification_overrides: dict[str, str] = field(default_factory=dict)


class Database:
    def rebuild_from_artifacts_and_mappings(self, settings: ReconstructionSettings | None = None) -> None:
        ...
```

- [ ] **Step 4: Re-run the reconstruction tests**

Run: `uv run pytest tests/test_store_schema.py tests/test_title_resolution.py -q`
Expected: PASS with session merge settings, duplicate posture, confidence thresholds, and classification override precedence wired through truth-building logic.

- [ ] **Step 5: Commit truth-layer config integration**

```bash
git add playtrace/store/db.py playtrace/merge/sessions.py playtrace/classify/resolver.py playtrace/services/scanner.py tests/test_store_schema.py tests/test_title_resolution.py
git commit -m "Wire config through reconstruction"
```

## Task 5: Integrate the Remaining Command Surface with the Resolver

**Files:**
- Modify: `playtrace/cli/cmd_titles.py`
- Modify: `playtrace/cli/cmd_sessions.py`
- Modify: `playtrace/cli/cmd_inspect.py`
- Modify: `playtrace/cli/cmd_sources.py`
- Modify: `playtrace/cli/cmd_map.py`
- Modify: `playtrace/cli/cmd_export.py`
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/services/inspector.py`
- Modify: `playtrace/services/sources.py`
- Modify: `playtrace/services/mapper.py`
- Modify: `playtrace/services/exporter.py`
- Modify: `tests/test_report_render.py`
- Modify: `tests/test_inspect_view.py`
- Modify: `tests/test_sources_command.py`
- Modify: `tests/test_export_service.py`
- Modify: `tests/test_mapping_service.py`
- Modify: `tests/test_command_config_integration.py`

- [ ] **Step 1: Write the failing tests for secondary command config defaults**

```python
def test_titles_uses_config_limit_when_cli_limit_is_unset(tmp_path: Path) -> None:
    seed_titles_database(tmp_path / "playtrace.db", ["Alpha", "Bravo"])
    result = runner.invoke(app, ["titles", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Alpha" in result.stdout
    assert "Bravo" not in result.stdout


def test_titles_cli_limit_overrides_config_limit(tmp_path: Path) -> None:
    seed_titles_database(tmp_path / "playtrace.db", ["Alpha", "Bravo"])
    result = runner.invoke(app, ["titles", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path), "--limit", "2"])
    assert result.exit_code == 0
    assert "Alpha" in result.stdout
    assert "Bravo" in result.stdout


def test_sessions_uses_config_days_when_cli_days_is_unset(tmp_path: Path) -> None:
    seed_sessions_database(tmp_path / "playtrace.db", recent_title="Recent Game", old_title="Old Game")
    result = runner.invoke(app, ["sessions", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Recent Game" in result.stdout
    assert "Old Game" not in result.stdout


def test_sessions_cli_days_override_config_days(tmp_path: Path) -> None:
    seed_sessions_database(tmp_path / "playtrace.db", recent_title="Recent Game", old_title="Old Game")
    result = runner.invoke(app, ["sessions", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path), "--days", "3"])
    assert result.exit_code == 0
    assert "Recent Game" in result.stdout
    assert "Old Game" in result.stdout


def test_export_uses_cli_format_over_config_format(tmp_path: Path) -> None:
    ExporterService().run(ExportRequest(db_path=tmp_path / "playtrace.db", config_path=config_path, raw=RawExportInput(format="json")))
    assert (tmp_path / "out.json").exists()


def test_map_uses_configured_auto_merge_posture_when_cli_auto_is_unset(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "[map]\nauto = true\n")
    stub = StubResolvedMapperService()
    monkeypatch.setattr("playtrace.cli.cmd_map.MapperService", lambda: stub)
    result = runner.invoke(app, ["map", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path)])
    assert result.exit_code == 0
    assert stub.calls[0].resolved.auto is True


def test_map_cli_no_auto_overrides_config_auto(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "[map]\nauto = true\n")
    stub = StubResolvedMapperService()
    monkeypatch.setattr("playtrace.cli.cmd_map.MapperService", lambda: stub)
    result = runner.invoke(
        app,
        ["map", "example.exe", "--title", "Example", "--db", str(tmp_path / "playtrace.db"), "--config", str(config_path), "--no-auto"],
    )
    assert result.exit_code == 0
    assert stub.calls[0].resolved.auto is False
```

- [ ] **Step 2: Run the secondary integration tests to verify the remaining commands still bypass config**

Run: `uv run pytest tests/test_command_config_integration.py tests/test_report_render.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_mapping_service.py -q`
Expected: FAIL because the remaining commands and services still hardcode request defaults.

- [ ] **Step 3: Implement resolver-backed settings for the remaining commands**

```python
class SourcesService:
    def render(self, request: SourcesRequest) -> None:
        resolved = self._resolve(request)
        ...


def map_title(...):
    raw = RawMapInput(auto=UNSET if auto_option_omitted else parsed_auto_value)
    resolved = ConfigResolver().resolve_map(...)
    validate_map_arguments_after_resolution(resolved, target, title)
    ...
```

- [ ] **Step 4: Re-run the secondary integration tests**

Run: `uv run pytest tests/test_command_config_integration.py tests/test_report_render.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_mapping_service.py -q`
Expected: PASS with config-backed defaults across `titles`, `sessions`, `inspect`, `sources`, `map`, and `export`, including direct command-entrypoint coverage for `titles`, `sessions`, and `map`.

- [ ] **Step 5: Commit secondary command config integration**

```bash
git add playtrace/cli/cmd_titles.py playtrace/cli/cmd_sessions.py playtrace/cli/cmd_inspect.py playtrace/cli/cmd_sources.py playtrace/cli/cmd_map.py playtrace/cli/cmd_export.py playtrace/services/reporter.py playtrace/services/inspector.py playtrace/services/sources.py playtrace/services/mapper.py playtrace/services/exporter.py tests/test_command_config_integration.py tests/test_report_render.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_mapping_service.py
git commit -m "Resolve config for remaining commands"
```

## Task 6: Validate `ready`, Update Validation Docs, and Run Full Verification

**Files:**
- Modify: `docs/VALTEST.md`
- Verify: `docs/config.example.toml`
- Verify: full suite and live CLI matrix

- [ ] **Step 1: Add config-specific validation cases to `docs/VALTEST.md`**

```markdown
### Config hierarchy validation

- default config behavior
- CLI override behavior
- missing config fallback
- missing active-profile fallback
- invalid config failure
- `ready` default profile behavior
```

- [ ] **Step 2: Run the focused config-related test suites**

Run: `uv run pytest tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py tests/test_store_schema.py tests/test_title_resolution.py tests/test_report_render.py tests/test_dashboard_service.py tests/test_audit_service.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_mapping_service.py -q`
Expected: PASS with config hierarchy, resolver precedence, and command integration covered.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS with the expanded config and command surface coverage.

- [ ] **Step 4: Run live CLI validation against temporary config files**

Run: `uv run python -m playtrace scan --db playtrace.db --config docs/config.example.toml`
Expected: renders `scan` using resolved defaults from config

Run: `uv run python -m playtrace me --db playtrace.db --config docs/config.example.toml`
Expected: renders `me` with the implicit `ready` profile

Run: `uv run python -m playtrace report --db playtrace.db --config docs/config.example.toml --theme mono`
Expected: renders `report` with CLI theme overriding config theme

Run: `uv run python -m playtrace doctor --db playtrace.db --config docs/config.example.toml`
Expected: renders `doctor` using configured thresholds and visibility defaults

Run: `uv run python -m playtrace titles --db playtrace.db --config docs/config.example.toml`
Expected: renders `titles` using resolved limit and theme defaults from config

Run: `uv run python -m playtrace sessions --db playtrace.db --config docs/config.example.toml`
Expected: renders `sessions` using resolved day-window and theme defaults from config

Run: `uv run python -m playtrace map --db playtrace.db --config docs/config.example.toml --auto`
Expected: uses resolved auto-merge posture and renders a successful mapping/merge result

Run: `uv run python -m playtrace report --db playtrace.db --config <temp-config-with-missing-profile>`
Expected: renders with built-in `ready` fallback and surfaces the fallback explicitly

- [ ] **Step 5: Commit validation documentation**

```bash
git add docs/VALTEST.md docs/config.example.toml
git commit -m "Document config hierarchy validation"
```

## Plan Review Checklist

Before execution starts:

- confirm every task still follows the approved spec in `docs/superpowers/specs/2026-04-17-config-hierarchy-design.md`
- confirm CLI precedence is always modeled as explicit user input over config
- confirm profiles remain optional power-user features rather than the default interaction requirement
- confirm reconstruction-affecting settings are implemented in the truth layer instead of display-only patches
- confirm the example config still represents the implicit `ready` experience clearly
