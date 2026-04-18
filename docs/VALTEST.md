# Validation Test Record

Date: `2026-04-17`
Repository: `C:\Users\ryanf\github\_new\playtrace`
Shell: `powershell`
Runtime: `uv` + Python `3.13.9`
Platform: Windows

Validation roots:

- Basics: `C:\Users\ryanf\AppData\Local\Temp\playtrace-valtest-20260417-141543`
- Flags/options: `C:\Users\ryanf\AppData\Local\Temp\playtrace-valflags-20260417-141908`
- Config hierarchy: `C:\Users\ryanf\AppData\Local\Temp\playtrace-config-val-20260417`

## Method

- Copied the existing root `playtrace.db` into isolated temp databases before each hands-on run.
- Ran the CLI through `uv run playtrace ...` from the repository root.
- Captured terminal output for every command into temp log files under the validation roots above.
- Fixed command-path defects as they were discovered, then re-ran the affected validations.
- Added a dedicated config hierarchy pass using `docs/config.example.toml` and a temporary missing-profile config.
- Finished with automated verification passes:
  - Focused config suite: `uv run pytest tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py tests/test_store_schema.py tests/test_title_resolution.py tests/test_report_render.py tests/test_dashboard_service.py tests/test_audit_service.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_mapping_service.py -q` -> `98 passed`
  - Full suite: `uv run pytest -q` -> `148 passed`

## Fixes Required During Validation

- Persisted resolved `title_id` values onto rebuilt sessions before saving them.
- Fixed timestamp-less start/exit evidence ordering so partial sessions are not created by bad sort order.
- Replaced scaffold/sample ingest collectors with live Windows collection for `userassist` and `security_log`.
- Removed legacy scaffold scan contamination by purging the exact historical sample scan runs from databases before rebuild.
- Replaced the flat config model with nested defaults, per-command blocks, optional profiles, and a shared resolver.
- Changed CLI option handling so omitted flags stay unset and config can supply the default behavior.
- Wired `scan`, `me`, `report`, `doctor`, `titles`, `sessions`, `inspect`, `sources`, `map`, and `export` through config resolution.
- Fed reconstruction settings through rebuilds for merge windows, classification overrides, duplicate auto-merge, duplicate thresholds, and evidence thresholds.
- Taught `inspect` to surface title-backed evidence even when no sessions exist.
- Taught title aggregation to use non-session evidence for launch counts, evidence sources, and foreground time.
- Counted GUI launches in `titles`, `report`, `me`, and export payloads.
- Normalized `sources` path targets so absolute executable paths resolve correctly.
- Made the security-log pipeline test deterministic instead of depending on host event-log state.

## Basic Command Validation

| Command | Status | Result |
| --- | --- | --- |
| `playtrace scan --db <copy> --theme mono` | Pass | Exit `0`. No fake sample titles were injected. Live `userassist` data was collected, unavailable sources stayed explicit, and the scan UI rendered a full summary. |
| `playtrace me --db <copy> --theme mono` | Pass | Exit `0`. Rendered the neofetch-style dashboard from live reconstructed data and audit notes. |
| `playtrace report --db <copy> --theme mono` | Pass | Exit `0`. Rendered live titles with non-session launch counts instead of scaffold placeholders. |
| `playtrace titles --db <copy> --theme mono` | Pass | Exit `0`. Rendered the title table without tracebacks. |
| `playtrace sessions --db <copy> --theme mono` | Pass | Exit `0`. Rendered a truthful empty-state when no sessions could be reconstructed on this machine. |
| `playtrace inspect --db <copy> --theme mono "battle.net launcher"` | Pass | Exit `0`. Surfaced `userassist` evidence ids and source counts without requiring sessions. |
| `playtrace sources --db <copy> --theme mono "battle.net launcher"` | Pass | Exit `0`. Listed `interactive_launch` and `foreground_usage` evidence rows. |
| `playtrace doctor --db <copy> --theme mono` | Pass | Exit `0`. Rendered diagnostics plus remediation guidance instead of crashing. |
| `playtrace export --db <copy> --output <file> --format json` | Pass | Exit `0`. Wrote JSON successfully. |
| `playtrace map --db <copy> --title "Battle.net Manual Validation" --classification launcher "<path>"` | Pass | Exit `0`. Persisted a manual mapping. |

## Config Hierarchy Validation

| Command | Status | Result |
| --- | --- | --- |
| `playtrace scan --db <copy> --config docs/config.example.toml` | Pass | Exit `0`. Used config-backed defaults, rendered the live scan summary, and collected from the default source set with unavailable sources still explicit. |
| `playtrace me --db <copy> --config docs/config.example.toml` | Pass | Exit `0`. Rendered the `ready` dashboard profile from stored data without requiring extra flags. |
| `playtrace report --db <copy> --config docs/config.example.toml --theme mono` | Pass | Exit `0`. Rendered successfully with explicit CLI theme overriding the config theme. |
| `playtrace doctor --db <copy> --config docs/config.example.toml` | Pass | Exit `0`. Rendered the diagnostics view through the shared config path. |
| `playtrace titles --db <copy> --config docs/config.example.toml --theme mono` | Pass | Exit `0`. Resolved limit/theme defaults through config and rendered the title table. |
| `playtrace sessions --db <copy> --config docs/config.example.toml --theme mono` | Pass | Exit `0`. Resolved day-window defaults through config and rendered a truthful empty-state. |
| `playtrace inspect --db <copy> --config docs/config.example.toml --theme mono "battle.net launcher"` | Pass | Exit `0`. Resolved through the config-backed request path and surfaced linked evidence. |
| `playtrace sources --db <copy> --config docs/config.example.toml --theme mono "battle.net launcher"` | Pass | Exit `0`. Resolved through the config-backed request path and listed source evidence rows. |
| `playtrace export --db <copy> --config docs/config.example.toml --output <file> --format json` | Pass | Exit `0`. Explicit CLI format overrode the config format and wrote JSON. |
| `playtrace map --db <copy> --config docs/config.example.toml --auto` | Pass | Exit `0`. Resolved auto-merge through config/CLI and merged `2` duplicate title groups in the validation copy. |
| `playtrace report --db <copy> --config <missing-profile.toml> --theme mono` | Pass | Exit `0`. Missing active profile fell back to built-in `ready` behavior and still rendered successfully. |

### Config precedence checks

- Missing `--theme`, `--density`, `--limit`, `--days`, `--format`, and `--auto` inputs now stay unset at the CLI boundary so config can provide defaults.
- Explicit CLI values win over config for `report --theme mono`, `titles --limit 2`, `sessions --days 365`, `export --format json`, and `map --no-auto`.
- Config default sources now drive `scan` when `--source` is omitted.
- Config `me.refresh = true` now triggers a scan before dashboard rendering when CLI refresh is omitted.

## Flag And Option Validation

| Command | Status | Result |
| --- | --- | --- |
| `playtrace scan --db <copy> --config <temp.toml> --source userassist --source security_log --full --theme mono --density compact` | Pass | Exit `0`. Explicit source selection worked and the compact scan view rendered correctly. |
| `playtrace me --db <copy> --refresh --theme mono` | Pass | Exit `0`. Forced a fresh scan before rendering the dashboard. |
| `playtrace report --db <scan-copy> --config <temp.toml> --theme mono --density compact --limit 5 --duplicates` | Pass | Exit `0`. Rendered the duplicates section and respected the lower title limit. |
| `playtrace titles --db <scan-copy> --theme mono --density compact --sort launches --classification launcher --limit 5` | Pass | Exit `0`. Rendered a clean empty-state when no launcher-classified titles matched current data. |
| `playtrace sessions --db <scan-copy> --theme mono --density compact --title "battle.net launcher" --days 3650 --limit 5` | Pass | Exit `0`. Rendered a clean empty-state for a title with no reconstructed sessions. |
| `playtrace inspect --db <scan-copy> --theme mono --density compact "C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"` | Pass | Exit `0`. Absolute path target normalized correctly and resolved the title-backed evidence. |
| `playtrace sources --db <scan-copy> --theme mono "C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"` | Pass | Exit `0`. Absolute path target normalized correctly after the fix. |
| `playtrace map --db <copy> --auto` | Pass | Exit `0`. Reported `Auto-merged 1 duplicate title group(s).` Post-run duplicate query returned `0` remaining duplicate groups in the validation copy. |
| `playtrace map --db <copy> --title "Ignore Battle.net" --classification launcher --ignore "<path>"` | Pass | Exit `0`. Persisted a mapping row with `ignore = 1`. |
| `playtrace export --db <scan-copy> --output <file> --format json` | Pass | Exit `0`. JSON export included `launches_gui` after the fix. |

## Machine-Specific Outcomes

- `security_log` returned no matching `4688`/`4689` events during the hands-on runs.
- `userassist` was the only live source producing evidence in this non-admin session.
- `prefetch` produced no accessible artifacts from the current process context.
- `amcache`, `srum`, and `bam` were unavailable from the current process context.
- Because exact runtime sources were unavailable in this session, reconstructed sessions stayed at `0` and runtime remained `unknown`. The CLI now renders that truthfully instead of inventing data.

## Observations

- `docs/config.example.toml` now drives real runtime behavior across the full public CLI surface instead of being a no-op.
- The missing-profile fallback currently resolves cleanly to built-in `ready` behavior and keeps rendering functional.
- The current live classification output still skews heavily toward `game` for `userassist`-only titles. That did not block command execution, but it does limit the usefulness of classification-based filtering.
- The validation above was run against isolated database copies. The source code now auto-purges the exact legacy scaffold scan runs that had previously polluted copied databases.

## Final Verification

- Focused config suite -> `98 passed`
- `uv run pytest -q` -> `148 passed`
