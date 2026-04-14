# Playtrace SPEC v2 Diff

This document is the design delta from the current Python scaffold to a stronger v2 spec. It keeps the scaffold's Python package structure and CLI ergonomics, but restores the evidence-first architecture and provenance guarantees from the earlier design docs.

## Decision Summary

SPEC v2 should **keep** the scaffold's repository layout, Typer command structure, SQLite baseline, and Rich rendering foundation. It should **restore** the earlier system model: raw evidence first, normalized evidence second, derived sessions and title aggregates last. It should **change** the current build order so exact evidence and provenance land before dashboard polish.

## Keep From the Current Scaffold

- Keep the package split across `cli/`, `services/`, `parsers/`, `normalize/`, `merge/`, `classify/`, `store/`, and `render/`.
- Keep Typer as the single CLI entrypoint and keep commands thin.
- Keep SQLite as the first storage backend.
- Keep typed dataclasses for request and model objects.
- Keep the theme and density concepts in the rendering layer.
- Keep the current command set: `scan`, `report`, `titles`, `sessions`, `inspect`, `map`, `doctor`, `export`.

## Restore From the Earlier Design

### 1. Evidence-First Pipeline

The scaffold currently trends toward a single in-memory artifact model. v2 should restore an explicit pipeline:

```text
Windows sources
  -> collectors
  -> raw artifact store
  -> parsers
  -> normalized evidence records
  -> executable normalization
  -> session merge
  -> classification and title resolution
  -> aggregates and renderers
```

Do not compute playtime during collection. Persist raw facts first, then derive sessions and title metrics from stored evidence.

### 2. Source Precedence and Honest Metrics

Restore the evidence precedence from the earlier spec:

1. Security Log 4688/4689 for exact sessions
2. Prefetch for strong execution history
3. UserAssist for interactive launch and focus signals
4. SRUM for coarse activity windows and network usage
5. AmCache for identity and first-seen anchors
6. BAM as optional weak supporting evidence

The CLI must keep exact and inferred values separate. Do not collapse them into one runtime or launch number.

### 3. Title Resolution as a First-Class Stage

The scaffold simplifies title aggregation too aggressively. v2 should restore:

- launcher-to-child resolution
- helper and runtime suppression
- manual title mapping
- title confidence separate from executable classification

The system is `exe-first, title-second`. A title is a derived view over related executables and sessions, not just `product_name` grouped into a row.

## Required Architecture Changes

### Split Raw Artifacts From Parsed Evidence

The current `ArtifactRecord` shape is too overloaded to be the canonical system boundary. v2 should use at least two layers:

- `RawArtifact`: source-native payload plus scan metadata and provenance
- `EvidenceRecord`: normalized semantic fact such as `process_start`, `process_exit`, `execution_count`, `interactive_launch`, `activity_window`, or `identity`

`ExecutableIdentity`, `SessionRecord`, and `TitleAggregate` remain downstream derived models.

### Add Missing Provenance Storage

The scaffold schema should add back the tables needed for replayable merges and transparent inspection:

- `artifacts`
- `scan_runs`
- `evidence_links`
- `title_executables`

Keep `executables`, `sessions`, `titles`, and `mappings`, but require that aggregates be rebuildable from stored artifacts plus user mappings.

### Refine Confidence Modeling

Do not use one enum to describe every kind of certainty. v2 should separate:

- source evidence strength: `exact`, `strong`, `interactive`, `weak`
- runtime confidence: `exact`, `estimated`, `unknown`
- mapping and classification confidence: `high`, `medium`, `low`, `unknown`

This preserves the honesty from the original design and avoids mixing precision with confidence.

### Expand Classification

Keep a primary classification bucket such as `game`, `launcher`, `helper`, `runtime`, `overlay`, `system`, `unknown`, and add optional subtypes such as `anti_cheat`, `crash_reporter`, `updater`, or `browser_wrapper`.

## Command and Behavior Changes

- Add a `sources` command to inspect provenance and source-specific evidence for an executable or title.
- Keep config-file support; a dedicated `config` command can stay deferred.
- `report` must stop seeding demo data as part of normal execution.
- `inspect` should show evidence provenance, launcher chains, and confidence reasoning.
- `scan` should persist raw artifacts and derived evidence separately.

## Build Order Changes

The scaffold's mock-first build order should be replaced with an evidence-first vertical slice:

1. Add provenance tables and scan run tracking.
2. Implement Security Log collection, parsing, and exact session pairing.
3. Implement executable normalization and identity keys.
4. Add Prefetch, UserAssist, and AmCache support.
5. Implement title resolution, manual mapping, and helper suppression.
6. Build `report`, `titles`, `sessions`, `inspect`, and `sources` on real stored data.
7. Add SRUM and BAM as corroborating sources.
8. Add visual polish, extra exports, and richer report modes.

`doctor` is still useful early, but it should validate coverage expectations, not substitute for the core data path.

## Testing Additions Required for v2

The current scaffold under-specifies testing. v2 should require:

- parser fixture tests per source
- exact-session pairing tests for 4688/4689
- dedupe and merge-window tests across sources
- title resolution and classifier rule tests
- schema and migration tests
- renderer snapshot tests for key report views

The acceptance bar is not "the report renders." The acceptance bar is that provenance, merge behavior, and confidence reporting are reproducible and testable.

## Explicit Non-Goals

- Do not invent exact runtime from weak sources.
- Do not make title aggregation depend only on filename or product name.
- Do not prioritize dashboard polish ahead of real evidence flow.
- Do not add ORM complexity before the raw-evidence model is stable.

## SPEC v2 Acceptance Criteria

SPEC v2 is satisfied when all of the following are true:

- every scan stores raw artifacts and scan metadata
- derived evidence can be traced back to source artifacts
- exact and inferred metrics remain separate in storage and UI
- title resolution uses launcher-child and mapping logic, not name grouping alone
- `inspect` and `sources` can explain why a title or session exists
- aggregates can be rebuilt from persisted artifacts and mappings
- test coverage exists for parsing, merging, title resolution, and reporting
