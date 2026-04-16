# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `playtrace me`, a stored-data identity dashboard with optional `--refresh` scanning.
- Added a structured audit engine for environment and persisted-data findings, plus remediation-aware `doctor` rendering.
- Added duplicate candidate surfacing in `report` and aggressive heuristic merging through `playtrace map --auto`.
- Added snapshot-driven export output and broader regression coverage across recovered CLI surfaces.

### Changed

- Reworked `scan` to render a source-status matrix and final summary instead of exiting silently.
- Rebuilt `report`, `titles`, and `sessions` on shared snapshot loaders and removed the remaining stub paths.
- Reintegrated `inspect`, `sources`, and `export` onto the same recovered truth layer used by the primary commands.
- Raised the baseline visual structure across `scan`, `me`, `report`, and `doctor` with clearer dashboard sections and degraded-state handling.

## [0.1.0] - 2026-04-14

### Added

- Evidence-first scan persistence with scan runs, raw artifacts, evidence links, rebuildable derived tables, and title-to-executable linkage.
- Source ingestion and parsing coverage for Security Log, Prefetch, UserAssist, AmCache, SRUM, and BAM.
- CLI support for `sources`, expanded provenance-aware `inspect`, and coverage-aware `doctor`.
- Regression coverage and fixtures for classification, session rebuilding, title resolution, inspect behavior, schema persistence, and source views.
- Exact Security Log session pairing and executable normalization for stable path/hash-based identities.
- Rebuildable executable, session, and title aggregation from persisted artifacts plus user mappings.

### Changed

- Normalized executable path handling so CLI mappings and inspect lookups resolve through the same internal `path:` identifiers as the rebuild pipeline.
- Title resolution now emits one result per active title cluster instead of collapsing unrelated executables into a single title.
- Scan run timestamps are now stored in UTC with explicit offsets.
- Executable rebuild typing now uses `ExecutableIdentity` directly instead of generic object storage.
- Security Log sample command line formatting now matches normal quoted Windows paths.
- `report` now renders persisted data only and no longer seeds demo rows.
- `inspect` now shows evidence source counts, mapping provenance, launcher parent chains, and confidence reasoning.
- `doctor` now explains expected runtime-confidence coverage from ingested evidence instead of acting as a simple environment check.

### Fixed

- Windows system binaries now classify correctly from `C:\Windows\...` paths.
- Mixed tz-naive and tz-aware evidence timestamps no longer crash session rebuilds.
- Invalid persisted mapping classifications no longer crash mapping loads.
- Session `evidence_ids` are now persisted and available in inspection output.
- Session id generation no longer collides when timestamps are missing.
- Ignore mappings now suppress matching executables during title resolution.
- Malformed PID values no longer abort session merging.
- Path-based manual mappings now survive rebuilds and apply during title resolution.
