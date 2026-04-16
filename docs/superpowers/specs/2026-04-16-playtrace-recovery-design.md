# Playtrace Recovery Design

## Goal

Recover Playtrace into a truthful, data-driven Windows CLI that:

- collects real evidence during `scan` and always renders a rich live UI
- reconstructs titles, sessions, duplicates, unmapped executables, and coverage from persisted evidence
- presents a neofetch-level static dashboard through `playtrace me`
- keeps `report` as a light snapshot while exposing deeper analysis behind flags
- turns `doctor` into both an environment diagnostic tool and a persisted-data audit tool
- never substitutes silence, placeholders, or fake confidence for missing data

This recovery is full-scope. It covers both command correctness and the underlying evidence pipeline that makes the commands believable.

## Problem Statement

Current `main` exposes a CLI surface that looks larger than the system actually is:

- `scan` performs ingestion but renders nothing
- `report` is backed by a partial snapshot model with obvious placeholder fields
- `titles` and `sessions` exist at the CLI layer but are still stubbed in the service layer
- `doctor` reports source readiness but does not diagnose the persisted database
- duplicate titles, weak title resolution, unknown runtimes, and unmapped executables are not surfaced coherently

The result is a tool that feels scaffolded instead of recovered. The fix is not to add more panels around existing behavior. The fix is to rebuild the pipeline first, then make every command render from that repaired truth layer.

## Product Decisions

The following decisions were established during design:

- `scan` is the live collection experience with progress, per-source status, warnings, and a final reconstruction summary.
- `playtrace me` is a new command. It is a neofetch-style static dashboard focused narrowly on Playtrace data.
- `me` defaults to stored data and uses `--refresh` to run a fresh scan before rendering.
- `report` remains a light recovered snapshot by default. Deeper analysis is exposed through flags instead of inflating the default surface.
- `doctor` audits both the environment and the existing database.
- Unknown or blocked states still render in the full UI. The CLI must explain how to improve collection or correct data quality.
- Duplicate handling is conservative by default. Suspected duplicates are surfaced. Aggressive heuristic merging is available behind `--auto`.
- Breaking CLI changes are acceptable when they are part of a coherent reintegration of the command surface.

## Design Principles

### 1. Truth Before Style

Rich CLI output is required, but the renderer may only express persisted evidence, explicit inference, or explicit uncertainty.

### 2. Always Render

Normal Windows limitations such as missing privileges, blocked files, sparse evidence, or unavailable collectors should not collapse the command into a blank or trivial output. They should become first-class findings in the UI.

### 3. Shared Snapshots, Thin Commands

Commands should compose typed snapshots and renderers. They should not contain business logic or ad hoc SQL.

### 4. Pipeline-First Recovery

The system should rebuild the evidence pipeline, reconstruction layer, and audit layer before treating the CLI as complete.

### 5. Remediation Is Part of the Product

Every degraded state should have either:

- a specific remediation step
- an explicit explanation of why no better data is currently available

## Command Contracts

### `playtrace scan`

Purpose:
- run live collection and reconstruction
- render a high-signal progress UI throughout the run

Required behavior:
- render a startup banner and selected source set
- show source-by-source progress and status transitions
- surface warnings, blocked sources, and partial failures during execution
- persist artifacts, evidence, and reconstruction results before final summary
- finish with a summary that includes evidence totals, reconstructed entities, confidence mix, and key findings

Must not:
- exit silently
- hide blocked or skipped sources

### `playtrace me`

Purpose:
- render a neofetch-style identity dashboard for Playtrace data

Required behavior:
- default to the latest stored reconstructed data
- support `--refresh` to run `scan` first
- focus on Playtrace data, not general machine trivia
- render narrow but high-quality sections such as coverage, top titles, evidence sources, scan freshness, and confidence posture
- show explicit unknowns and collection gaps when evidence is weak

Must not:
- expand into a general-purpose system info command

### `playtrace report`

Purpose:
- render a light recovered snapshot of the current state

Required behavior:
- show a concise summary by default
- load only from reconstructed entities and audit summaries
- support deeper flags for duplicates, unmapped executables, evidence quality, or session detail

Must not:
- contain hardcoded totals
- pretend that absent data is authoritative

### `playtrace titles`

Purpose:
- render filtered and sorted title aggregates from reconstructed data

Required behavior:
- support filtering and sorting from a shared snapshot builder
- show launcher, confidence, runtime, launches, and duplicate suspicion cleanly
- degrade invalid persisted enum values to `UNKNOWN`, not exceptions

### `playtrace sessions`

Purpose:
- render reconstructed session rows truthfully

Required behavior:
- handle exact, estimated, and partial sessions
- render open or incomplete sessions explicitly
- show unknown runtime as unknown, not zero

### `playtrace doctor`

Purpose:
- diagnose both the current environment and the persisted database

Required behavior:
- report source readiness, permissions, blocked paths, and collector prerequisites
- audit duplicate titles, fragmented sessions, unmapped executables, stale scans, sparse evidence, and weak confidence
- include corrective guidance sections

### `playtrace inspect`, `playtrace sources`, `playtrace map`, and `playtrace export`

Purpose:
- expose detailed slices of the same reconstructed truth layer

Required behavior:
- read from shared normalized, reconstructed, and audited models
- remain consistent with `scan`, `report`, `titles`, `sessions`, and `doctor`
- surface unknowns, blocked evidence, and remediation context rather than failing on sparse data
- adopt any breaking argument changes required to align with the recovered command model

Must not:
- depend on stale bespoke logic that disagrees with the primary snapshots

### Duplicate Remediation Surface (`report --duplicates`, or equivalent report flag surface)

Purpose:
- surface suspected duplicate groups and give the user a safe path to resolve them

Required behavior:
- show candidate groups, evidence supporting the suspicion, and likely outcome of merge
- keep default mode advisory
- allow aggressive heuristic merging through `--auto`
- re-run reconstruction and re-render the affected snapshot after merge

## Recovery Architecture

The recovery is organized into five layers.

### 1. Collection Foundation

Responsibilities:
- source selection
- permission-aware collector execution
- progress event emission
- artifact capture
- scan-run lifecycle persistence

Outputs:
- persisted scan run metadata
- raw artifacts
- progress events for the `scan` renderer

### 2. Normalization and Evidence Graph

Responsibilities:
- parse artifacts into typed evidence
- normalize paths, executables, metadata, and provenance
- preserve enough source detail that later commands can explain why a title or session exists

Outputs:
- typed evidence records with source, strength, timestamps, and normalized identity references

### 3. Reconstruction Engine

Responsibilities:
- rebuild executables
- rebuild sessions
- rebuild titles
- detect duplicate candidates
- identify unmapped executables
- assign confidence levels and coverage posture

Outputs:
- reconstructed entities and derived findings that are stable enough for all CLI surfaces

### 4. Health and Remediation Layer

Responsibilities:
- diagnose the current machine environment
- diagnose the persisted database and reconstruction quality
- produce ordered findings with remediation guidance

Outputs:
- doctor findings
- remediation suggestions
- duplicate and weak-data findings reused by other commands

### 5. Presentation Layer

Responsibilities:
- render each command from a shared snapshot
- keep output expressive without fabricating data

Outputs:
- rich live scan views
- neofetch-style `me` dashboard
- concise `report`
- detail views for titles and sessions
- audit-heavy `doctor`

## Data Flow

### Scan Path

1. `scan` starts a scan run and selects sources.
2. Collectors emit progress events and raw artifacts.
3. Artifacts are persisted immediately.
4. Parsers convert artifacts into typed evidence.
5. Normalizers resolve executable identity and metadata.
6. Reconstruction builds executables, sessions, titles, duplicates, unmapped items, and confidence summaries.
7. Final summaries are persisted and rendered.

### Stored-Data Paths

`me`, `report`, `titles`, `sessions`, and `doctor` should load from persisted reconstructed truth.

`me --refresh` is the one exception: it runs the scan path first, then renders from the newly persisted state.

### Audit Path

`doctor` runs two streams:

- environment diagnostics
- data-quality diagnostics

Those are merged into a single doctor snapshot with severity, evidence, and remediation.

## Snapshot Model

The command layer should be refactored around shared snapshot builders rather than direct command-specific queries.

Required snapshot types:

- `ScanLiveSnapshot`
- `IdentityDashboardSnapshot` for `me`
- `ReportSnapshot`
- `TitlesSnapshot`
- `SessionsSnapshot`
- `DoctorSnapshot`

Common snapshot traits:

- generated timestamp
- scan freshness or provenance
- confidence and coverage metadata
- explicit unknown state support
- remediation attachments where relevant

## Unknown, Sparse, and Blocked States

The CLI should use explicit degraded states instead of hiding weak data.

Examples:

- missing process exit evidence -> runtime shown as `UNKNOWN` or `PARTIAL`
- inaccessible SRUM database -> source shown as blocked with remediation
- no mapped title -> executable shown under unmapped or raw identity group
- invalid legacy enum value -> downgraded to `UNKNOWN`
- stale latest scan -> stale-data warning attached to `me`, `report`, and `doctor`

Each degraded state should include one of:

- `How to improve this`
- `Why this is unknown`
- `What flag or follow-up action to use next`

## Duplicate Handling

Duplicate handling belongs in reconstruction and audit, not just UI.

Default behavior:
- identify and surface suspected duplicates
- show the evidence behind each candidate group
- recommend likely merges or manual mapping actions

`--auto` behavior:
- apply aggressive heuristic merging
- persist the resulting title/session rebuild
- keep an audit trail of what changed
- immediately re-render the relevant output so the result is visible

The heuristic system should consider:

- normalized executable identity overlap
- original filename / product name / file description similarity
- launcher overlap
- session timing patterns
- user mapping history
- evidence-source consistency

## Rendering System

The presentation layer should be rebuilt around reusable sections instead of one-off panels:

- command headers
- metric cards
- progress/status rows
- tables for titles and sessions
- duplicate candidate groups
- warnings and remediation panels
- neofetch-style key/value identity blocks

Presentation requirements:

- visually strong ASCII/Rich output
- clear distinction between exact, estimated, partial, and unknown
- no placeholder values
- remediation guidance integrated into the command output rather than hidden behind separate docs

## Error Handling

Commands should fail soft for normal operational problems and fail hard only for actual program breakage.

Fail soft:
- permission denied on optional sources
- missing collector prerequisites
- sparse evidence
- unknown launcher or title
- invalid legacy persisted values

Fail hard:
- incompatible schema that cannot be read
- internal programming errors
- invalid command contract assumptions that would corrupt persisted state

Soft failure always means:
- render the command
- mark the issue explicitly
- attach remediation guidance

## Testing Strategy

This recovery requires end-to-end behavioral testing, not only unit scaffolding.

### Pipeline Tests

- collector and orchestrator tests for progress events, warnings, and partial failure handling
- evidence parsing and normalization tests
- reconstruction tests for executables, titles, sessions, duplicates, unmapped entities, and confidence assignment

### Snapshot Tests

- `me` snapshot from both healthy and degraded data
- `report` snapshot default mode and deep-flag expansions
- `titles` and `sessions` filtering and ordering
- `doctor` snapshot from both environment and persisted audit streams

### Render Tests

- live scan progress rendering
- neofetch-style `me` layout
- degraded states with explicit unknowns
- remediation panel rendering
- duplicate candidate rendering and `--auto` result rendering

### CLI Tests

- command contracts and breaking-surface updates
- flag behavior for `--refresh`, `--auto`, and deep report options
- no silent command exits

### Windows Integration Checks

- permissions-sensitive collectors
- blocked-source detection
- path and metadata normalization against real Windows fixtures where possible

## Phased Delivery

This is one recovery initiative, but it should still be implemented in phases.

### Phase 1: Rebuild the Core Truth Layer

- scan-run persistence
- evidence normalization
- reconstruction of executables, sessions, titles
- duplicate candidate detection
- unmapped and confidence findings

### Phase 2: Recover the Command Semantics

- `scan`
- `me`
- `titles`
- `sessions`
- `report`
- `doctor`
- `inspect`
- `sources`
- `map`
- `export`

### Phase 3: Raise the Visual Quality Bar

- live scan presentation polish
- neofetch-style identity dashboard
- remediation and duplicate surfaces
- consistent themed sections across commands

## Risks

- Windows source access is inherently uneven across privilege levels and machine state
- aggressive duplicate merging can destroy trust if audit visibility is weak
- visual polish will drift into placeholder output again if command renderers bypass shared snapshots
- breaking CLI changes require a coherent migration of help text, docs, and tests in the same implementation pass

## Success Criteria

Playtrace is recovered when:

- every public command renders a useful rich UI
- no command depends on placeholder snapshot values
- the persisted evidence pipeline explains why titles and sessions exist
- degraded states remain visible and actionable
- `scan` feels alive
- `me` feels polished
- `doctor` finds real problems and explains how to fix them
