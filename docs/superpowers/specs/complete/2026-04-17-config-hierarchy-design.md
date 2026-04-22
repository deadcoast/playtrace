# Playtrace Config Hierarchy Design

## Goal

Turn Playtrace configuration into the application's real default-behavior layer so that:

- the app has one coherent hierarchy for defaults and overrides
- ordinary users get a strong out-of-the-box experience without learning config internals
- explicit CLI inputs always override config defaults
- command behavior, reconstruction behavior, and presentation behavior all resolve through the same contract
- the `ready` experience is the implicit default QoL showcase without requiring users to select a spec manually

This design extends Playtrace's documented recovery direction. It does not trim features or replace documented command surfaces with a smaller shortcut model.

## Problem Statement

Playtrace currently exposes `--config`, but the live command paths do not consume it in a meaningful way. The existing config model is also too narrow to support the actual product shape:

- it only covers a small set of fields
- it does not represent command defaults
- it does not model presentation defaults
- it does not model reconstruction defaults
- it does not provide a first-class default showcase profile
- it does not provide one shared precedence contract across commands

The result is misleading: the CLI appears configurable, but the behavior remains mostly hardcoded.

## Product Decisions

The following decisions were established during design:

- configuration is the default behavior layer for the application
- explicit CLI inputs always override configuration defaults
- the config is organized around one shared defaults block plus per-command blocks
- optional named profiles exist for power users, but are not required for ordinary use
- `ready` is the implicit default profile and should showcase the strongest QoL path
- the `ready` profile focuses on high-value functionality and presentation, not on surfacing every possible advanced knob
- config must cover real behavior, not only renderer options
- reconstruction-affecting config must flow through the truth layer, not through display-only patches

## Design Principles

### 1. Config Is Behavior, Not Decoration

Configuration must define how Playtrace behaves by default, not just how it looks.

### 2. One Hierarchy Everywhere

Every public command should resolve settings through the same precedence model.

### 3. CLI Intent Wins

If the user explicitly passes a CLI option, that value takes priority over everything else.

### 4. Great Defaults for Normal Users

The application should feel polished and understandable without forcing users to learn config syntax, profile names, or internal behavior flags.

### 5. Profiles Are Optional Power Tools

Profiles should improve advanced workflows without becoming a prerequisite for normal usage.

### 6. No Display-Only Lies

If a setting changes how titles, sessions, duplicates, confidence, or coverage are derived, it must flow through reconstruction or shared query semantics, not just repaint the output.

## Configuration Shape

The config file should be structured around four concepts:

### 1. `[defaults]`

Shared defaults that apply across commands unless a command block overrides them.

Typical responsibilities:

- database path default
- theme and density defaults
- active default profile name
- source-selection defaults
- reconstruction defaults
- shared presentation defaults

### 2. Per-command blocks

Each public command gets its own block:

- `[scan]`
- `[me]`
- `[report]`
- `[doctor]`
- `[titles]`
- `[sessions]`
- `[inspect]`
- `[sources]`
- `[map]`
- `[export]`

Each block should contain only that command's defaults. This keeps the file understandable for users who just want to tune one command.

### 3. `[profiles.ready]`

`ready` is the implicit default profile. It exists to showcase the strongest day-to-day Playtrace experience:

- visually rich `scan`
- polished neofetch-style `me`
- concise but truthful `report`
- actionable `doctor`

It should enable the highest-value parts of the product without turning the default path into a kitchen-sink feature dump.

### 4. Optional additional profiles

Examples:

- `[profiles.minimal]`
- `[profiles.forensics]`
- `[profiles.quiet]`

These are for advanced users and future growth. The application must still feel complete without them.

## Example TOML Shape

```toml
[defaults]
active_profile = "ready"
theme = "midnight"
density = "comfortable"
default_sources = ["security_log", "userassist", "prefetch"]

[defaults.reconstruction]
session_merge_dedupe_window_minutes = 2
duplicate_auto_merge = false

[defaults.classification]
overrides = { "C:\\Games\\MyGame.exe" = "game" }

[scan]
full = false
show_summary = true
show_warnings = true
show_duplicates = true
show_unmapped = true

[me]
refresh = false
show_warnings = true
show_remediation = true
top_titles_limit = 5

[report]
limit = 10
show_duplicates = true
show_unmapped = true
show_sparse_evidence = true

[doctor]
show_passing_checks = false
show_remediation = true
severity = "low"

[profiles.ready]
theme = "midnight"
density = "cinematic"

[profiles.ready.scan]
show_summary = true
show_duplicates = true
show_unmapped = true

[profiles.ready.me]
show_warnings = true
show_remediation = true

[profiles.ready.report]
show_duplicates = true

[profiles.ready.doctor]
show_remediation = true
```

The exact field names can evolve during implementation, but the structure should match this hierarchy.

## Precedence Rules

The resolver should apply configuration in this order:

1. built-in application defaults
2. config `[defaults]`
3. active profile overrides, with `ready` active by default
4. per-command block overrides such as `[scan]` or `[report]`
5. explicit CLI inputs

CLI input always wins.

Important implementation detail:

The CLI layer must distinguish between:

- a value explicitly provided by the user
- a value left unset by the user

Parser defaults must not be treated as explicit user intent, or they will mask config values.

## Runtime Architecture

Configuration resolution should be centralized in a shared runtime layer.

### `ConfigLoader`

Responsibilities:

- parse TOML
- validate the config model
- return a full typed config object

It should not contain command-specific precedence logic.

### `ConfigResolver`

New component.

Inputs:

- built-in defaults
- loaded config
- target command name
- optional requested profile name
- raw CLI inputs with explicit unset support

Outputs:

- one typed resolved settings object for the target command

### Raw CLI input models

Each command should pass a raw input model that preserves whether each field was actually set by the user.

### Resolved settings models

Each command should receive a typed resolved settings object, for example:

- `ResolvedScanSettings`
- `ResolvedMeSettings`
- `ResolvedReportSettings`
- `ResolvedDoctorSettings`

Services should consume resolved settings only. They should not inspect TOML structures directly.

## Settings Domains

Resolved settings should be split into three domains.

### 1. Collection settings

Examples:

- selected sources
- full vs incremental scan default
- refresh behavior

### 2. Reconstruction settings

Examples:

- session merge dedupe window
- duplicate detection defaults
- duplicate auto-merge posture
- classification overrides
- evidence and confidence thresholds

These affect reconstructed truth and must flow through the rebuild layer, not only the renderer.

### 3. Presentation settings

Examples:

- theme
- density
- section visibility
- card and table layout choices
- remediation emphasis

These affect rendering only and should remain command-specific where appropriate.

## Command Contracts

### `scan`

Config should control:

- default source selection
- default scan mode
- visual richness defaults
- progress verbosity
- summary sections such as duplicates, unmapped executables, and warnings

`ready` behavior:

- strong live visual output
- essential data surfaced
- blocked and missing sources shown explicitly
- no silent or trivial output

### `me`

Config should control:

- refresh default
- visible sections
- warning and remediation visibility
- title/session card density
- layout flavor

`ready` behavior:

- lightweight but polished neofetch-style dashboard
- essential metrics only
- explicit unknowns and correction guidance when data is weak

### `report`

Config should control:

- title limit
- duplicate visibility
- unmapped and sparse-evidence sections
- summary depth and sort defaults

`ready` behavior:

- concise but truthful recovered snapshot
- highest-value operational sections enabled by default

### `doctor`

Config should control:

- enabled environment checks
- enabled data-audit checks
- surfaced severity threshold
- remediation visibility
- whether passing checks are rendered

`ready` behavior:

- findings first
- causes second
- correction guidance always present

### `titles`

Config should control:

- sort defaults
- filter defaults
- duplicate indicators
- limit
- confidence rendering posture

### `sessions`

Config should control:

- time window defaults
- limit
- grouping defaults
- partial/open session rendering

### `inspect`, `sources`, `map`, and `export`

Config should still provide useful defaults for:

- output depth
- normalization behavior
- auto-merge defaults
- export format and scope defaults

These commands remain focused tools, not showcase commands.

## `ready` Profile Contract

`ready` is the implicit default QoL profile. It should:

- make `scan` feel alive
- make `me` feel polished
- make `report` feel useful immediately
- make `doctor` feel corrective rather than passive
- prefer strong defaults for the primary surfaces
- avoid exposing every low-value advanced option by default

`ready` is not a replacement for the general config hierarchy. It is the default opinion layered on top of it.

## Behavior Integration

The config hierarchy must control real behavior in three areas.

### Collection defaults

This includes:

- default sources
- default scan mode
- command refresh defaults
- output defaults for collection flows

### Reconstruction defaults

This includes:

- session merge behavior
- title resolution defaults
- duplicate handling posture
- classification overrides
- evidence and confidence thresholds

These settings must flow through reconstruction or shared loaded-query semantics.

### Presentation defaults

This includes:

- theme
- density
- section visibility
- layout flavor
- remediation emphasis

## Precedence Inside Reconstruction

When config influences title classification or mapping-like behavior, precedence should be:

1. explicit CLI and explicit user actions
2. persisted user mappings
3. config defaults and profile defaults
4. heuristics

This keeps beginner behavior strong while preserving a clear path to advanced manual control.

## Error Handling

Configuration problems should fail clearly. Weak Windows data should degrade cleanly.

Fail fast:

- invalid TOML
- invalid config field values
- invalid command blocks
- invalid profile definitions
- unsupported source names, modes, sort keys, severity values, or themes

Degrade cleanly:

- missing command block
- missing optional profile
- weak or missing Windows evidence
- blocked sources
- sparse reconstructed data

If the configured active profile is missing, the app should fall back to built-in `ready` behavior and surface that fallback explicitly.

Unknown top-level fields may still be ignored for compatibility, but malformed known structures should not be silently accepted.

## Testing Strategy

This configuration redesign requires more than parser tests.

### Loader and model tests

Validate:

- `[defaults]`
- per-command blocks
- profile parsing
- invalid values
- compatibility behavior for unknown fields

### Resolver tests

Validate the exact precedence chain:

- built-in defaults
- config defaults
- active profile
- command block
- CLI overrides

This is the core correctness surface.

### Command integration tests

Validate that commands actually consume resolved settings, especially:

- `scan`
- `me`
- `report`
- `doctor`

### Reconstruction tests

Validate config-driven behavior for:

- session merge window
- classification overrides
- duplicate-policy defaults
- confidence/evidence thresholds where implemented

### Render and behavior tests

Validate:

- section visibility
- density and theme defaults
- remediation defaults
- `ready` showcase behavior

### Hands-on validation

Re-run the documented matrix in `docs/VALTEST.md` against:

- no config
- valid config defaults
- valid config plus CLI overrides
- missing config fallback
- invalid config failure
- `ready` default behavior

## Implementation Outline

1. expand the config model to represent shared defaults, command blocks, and profiles
2. add raw CLI input models with explicit unset tracking
3. add a shared `ConfigResolver`
4. refactor commands to resolve settings before entering services
5. refactor services to accept resolved settings instead of ad hoc defaults
6. wire reconstruction-affecting config into the truth layer
7. wire presentation config into render paths
8. add resolver, integration, and validation coverage

## Risks

- parser-default leakage can quietly defeat config precedence if unset values are not preserved
- reconstruction-affecting config can drift from persisted truth if implemented as renderer-only overrides
- profile inheritance can become confusing if it is allowed to bypass the main defaults hierarchy
- overloading `ready` with too many advanced behaviors will dilute the QoL goal

## Success Criteria

This design is successful when:

- Playtrace has one coherent default-behavior hierarchy
- ordinary users get a strong experience without learning config internals
- explicit CLI inputs always override config cleanly
- `ready` is the implicit default QoL profile
- configuration changes affect real command behavior consistently
- configuration precedence is proven in tests
