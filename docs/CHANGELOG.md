# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-14

### Added

- Evidence-first scan persistence with scan runs, raw artifacts, evidence links, rebuildable derived tables, and title-to-executable linkage.
- Source ingestion and parsing coverage for Security Log, Prefetch, UserAssist, AmCache, SRUM, and BAM.
- CLI support for `sources`, expanded provenance-aware `inspect`, and coverage-aware `doctor`.
- Regression coverage and fixtures for classification, session rebuilding, title resolution, inspect behavior, schema persistence, and source views.

### Changed

- Normalized executable path handling so CLI mappings and inspect lookups resolve through the same internal `path:` identifiers as the rebuild pipeline.
- Title resolution now emits one result per active title cluster instead of collapsing unrelated executables into a single title.
- Scan run timestamps are now stored in UTC with explicit offsets.
- Executable rebuild typing now uses `ExecutableIdentity` directly instead of generic object storage.
- Security Log sample command line formatting now matches normal quoted Windows paths.

### Fixed

- Windows system binaries now classify correctly from `C:\Windows\...` paths.
- Mixed tz-naive and tz-aware evidence timestamps no longer crash session rebuilds.
- Invalid persisted mapping classifications no longer crash mapping loads.
- Session `evidence_ids` are now persisted and available in inspection output.
- Session id generation no longer collides when timestamps are missing.
- Ignore mappings now suppress matching executables during title resolution.
- Malformed PID values no longer abort session merging.
