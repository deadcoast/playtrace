# TODO

This file tracks the PR review findings for PR #1 and records their current state in a consistent format.

Verification scope:
- Branch: `spec-v2`
- Verified commit: `5151da7`
- Fresh checks run for this review pass:
  - `uv run pytest` -> `28 passed`
  - `uv run python -m playtrace --help` -> passed
  - `uv run python -m playtrace sources --help` -> passed
  - `uv run python -m playtrace doctor --help` -> passed

## Review Items

### BUG-01 System path classification
- Status: Completed and verified
- Source: manual review, Codex review, Copilot review
- Summary: `classify_executable()` did not match normal `C:\Windows\...` paths because the prefix literal was wrong.
- Fix: [playtrace/classify/rules.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/classify/rules.py>) now uses `startswith("c:\\windows\\")`.
- Verification: `tests/test_classification.py::test_classify_executable_marks_windows_binaries_as_system`

### BUG-02 Mixed timezone handling in evidence/session rebuild
- Status: Completed and verified
- Source: manual review, Codex review, Copilot review
- Summary: mixed tz-naive and tz-aware datetimes could crash session sorting and rebuild.
- Fix: [playtrace/ingest/amcache.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/ingest/amcache.py>) now emits UTC-aware timestamps, and [playtrace/merge/sessions.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/merge/sessions.py>) coerces naive values to UTC before sorting and duration math.
- Verification: `tests/test_merge_sessions.py::test_session_merger_coerces_naive_timestamps_to_utc`

### BUG-03 Path mappings never applied
- Status: Completed and verified
- Source: manual review, Copilot review
- Summary: `playtrace map` stored raw filesystem paths while title resolution matched normalized `path:` executable ids.
- Fix: [playtrace/services/mapper.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/services/mapper.py>) and [playtrace/normalize/identity.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/normalize/identity.py>) normalize raw paths to internal ids, and [playtrace/classify/resolver.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/classify/resolver.py>) matches normalized mapping keys.
- Verification: `tests/test_mapping_service.py::test_mapper_normalizes_raw_path_targets`

### BUG-04 Invalid mapping classification crashes load
- Status: Completed and verified
- Source: manual review
- Summary: invalid user-provided `classification` strings could raise `ValueError` when mappings were loaded.
- Fix: [playtrace/cli/cmd_map.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/cli/cmd_map.py>) now uses the `Classification` enum for CLI input, and [playtrace/store/db.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/store/db.py>) safely ignores invalid persisted enum values.
- Verification: `tests/test_store_schema.py::test_load_user_mappings_ignores_invalid_classification`

### BUG-05 Session evidence ids were not persisted
- Status: Completed and verified
- Source: manual review, Copilot review
- Summary: derived sessions carried `evidence_ids`, but SQLite dropped them.
- Fix: [playtrace/store/schema.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/store/schema.py>) adds `sessions.evidence_ids`, [playtrace/store/db.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/store/db.py>) persists it, and [playtrace/services/inspector.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/services/inspector.py>) surfaces it.
- Verification: `tests/test_store_schema.py::test_replace_sessions_persists_evidence_ids`, `tests/test_inspect_view.py::test_inspect_view_shows_confidence_and_parent_chain`

### BUG-06 Session ids could collide when timestamps were missing
- Status: Completed and verified
- Source: manual review
- Summary: `_session_id()` used a constant fallback timestamp, which could generate duplicate primary keys.
- Fix: [playtrace/merge/sessions.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/merge/sessions.py>) now includes stable fallback fragments and `record.evidence_id` in the generated id.
- Verification: `tests/test_merge_sessions.py::test_session_merger_uses_evidence_id_when_timestamp_missing`

### BUG-07 Ignore mappings were not applied
- Status: Completed and verified
- Source: reviewer comment, Codex review
- Summary: ignore mappings were filtered out before executable classification, so `map --ignore` had no effect.
- Fix: [playtrace/classify/resolver.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/classify/resolver.py>) keeps ignore mappings in lookup and suppresses matching executables.
- Verification: `tests/test_title_resolution.py::test_ignore_mapping_suppresses_executable`

### BUG-08 Independent titles were collapsed into one result
- Status: Completed and verified
- Source: Codex review
- Summary: the resolver always returned a single `ResolvedTitle`, dropping additional active titles during rebuild.
- Fix: [playtrace/classify/resolver.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/classify/resolver.py>) now groups active executables into distinct title clusters and emits one resolved title per cluster.
- Verification: `tests/test_title_resolution.py::test_title_aggregator_emits_multiple_titles_for_independent_games`

### BUG-09 Inspect did not resolve raw executable paths
- Status: Completed and verified
- Source: Copilot review
- Summary: `inspect` only matched title names, title ids, or exact stored executable ids.
- Fix: [playtrace/services/inspector.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/services/inspector.py>) now normalizes raw path targets and resolves through `title_executables` and `sessions`.
- Verification: `tests/test_inspect_view.py::test_inspect_view_accepts_raw_executable_paths`

### BUG-10 Scan run timestamps were stored as naive datetimes
- Status: Completed and verified
- Source: Copilot review
- Summary: `create_scan_run()` and `finish_scan_run()` wrote timestamps without timezone offsets.
- Fix: [playtrace/store/db.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/store/db.py>) now stores scan run timestamps in UTC with explicit offsets.
- Verification: `tests/test_store_schema.py::test_scan_runs_store_timezone_aware_timestamps`

### BUG-11 Unparseable PIDs could abort session merging
- Status: Completed and verified
- Source: reviewer comment
- Summary: `pid = int(pid)` raised for malformed payloads and stopped rebuild.
- Fix: [playtrace/merge/sessions.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/merge/sessions.py>) now treats invalid PID values as `None`.
- Verification: `tests/test_merge_sessions.py::test_session_merger_treats_unparseable_pid_as_none`

### CLEANUP-01 Executable rebuild typing
- Status: Completed and verified
- Source: Copilot review
- Summary: `executable_map` was typed as `dict[str, object]` even though it stored `ExecutableIdentity`.
- Fix: [playtrace/store/db.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/store/db.py>) now uses `dict[str, ExecutableIdentity]`.
- Verification: verified in code review and covered by the full `uv run pytest` pass

### CLEANUP-02 Sample security log command line formatting
- Status: Completed and verified
- Source: Copilot review
- Summary: the sample command line used a literal `\"` prefix instead of a normal quoted Windows path.
- Fix: [playtrace/ingest/security_log.py](</C:/Users/ryanf/.config/superpowers/worktrees/playtrace/spec-v2/playtrace/ingest/security_log.py>) now stores a normal quoted command line sample.
- Verification: verified in code review and covered by the full `uv run pytest` pass
