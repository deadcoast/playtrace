# Playtrace Duplicate Detection Performance Design

## Goal

Complete the deferred duplicate-detection follow-up by removing the naive full pairwise scan from `TitleResolver` while preserving Playtrace's reconstruction-first duplicate reasoning and existing `DuplicateCandidate` output contract.

This pass is intentionally narrow. It optimizes duplicate candidate generation inside the resolver. It does not reduce documented duplicate reasoning, move duplicate semantics into the database, or change the command/report/export surface shape.

## Problem Statement

The current duplicate candidate pass in `playtrace/classify/resolver.py` performs a pairwise comparison across the full resolved-title list:

1. walk titles in order
2. compare each title with every later title
3. call `_duplicate_reasons()` for each pair
4. group verified matches and choose a primary title

That implementation is acceptable for small title sets, but it is still the known scalability outlier from the reconstruction and lineage pass. As title counts grow, obviously unrelated reconstructed title surfaces still incur unnecessary verification work.

The correct fix is not to weaken duplicate detection into simple string blocking. The correct fix is to separate search-space reduction from duplicate proof so Playtrace keeps evidence-oriented, reconstruction-oriented duplicate reasoning.

## Product Decisions

The following decisions were established during design approval:

- use the `bucket + verify` approach
- keep the work inside `TitleResolver`
- preserve the existing `DuplicateCandidate` output shape
- preserve existing primary-title selection behavior
- treat blocking as a search-space reduction step only
- keep duplicate verification multi-signal and reconstruction-oriented
- keep launcher ancestry as surfaced reasoning, but do not let it create broad false-positive duplicate groups by itself
- validate the change with correctness regressions first, then scale-oriented verification-fanout tests

## Design Principles

### 1. Reconstruction Semantics Stay Intact

Playtrace duplicate candidates represent suspected duplicate reconstructed title surfaces, not merely similar strings. Optimization must not collapse the feature into a weaker title-matching shortcut.

### 2. Search Space Reduction Is Not Duplicate Proof

Blocking decides which pairs are worth checking. Verification still decides whether two reconstructed title surfaces are related strongly enough to surface as suspected duplicates.

### 3. No Silent De-Scoping

This change may reorganize the duplicate-detection algorithm, but it must not remove documented reasoning dimensions under the label of optimization.

### 4. Output Stability Matters

`report`, `export`, mapping preview flows, and renderers should not need contract churn for this pass. The resolver should still emit the same `DuplicateCandidate` structure.

## Scope

### In Scope

- duplicate-candidate generation inside `TitleResolver`
- resolver-local fingerprinting and blocking data structures
- verification-stage tightening where needed to keep duplicate proof separate from support signals
- correctness regression tests
- scale-oriented tests based on verification fanout
- documentation updates tied to the deferred follow-up

### Out Of Scope

- database-side duplicate generation
- render-layer redesign
- command-surface redesign
- changing persisted duplicate candidate schema
- broad reconstruction heuristic changes outside duplicate candidate generation

## Current Behavior

The current implementation in `_duplicate_candidates()`:

- scans the full title list in order
- compares each title to every later title
- asks `_duplicate_reasons()` whether the pair should be grouped
- chooses the primary title by title confidence, normalized-title quality, and lexical tiebreakers

This means the expensive part of duplicate detection scales with all possible title pairs instead of with plausible duplicate neighborhoods.

## Proposed Architecture

The optimized resolver path should use two explicit stages: `block` and `verify`.

### Stage 1: Fingerprint

Each resolved title surface gets one lightweight fingerprint record containing:

- `title_id`
- original title
- normalized title
- informative normalized tokens
- normalized length band
- launcher key
- index position for deterministic ordering

The fingerprint is internal to the resolver and does not change persisted models.

### Stage 2: Block

The resolver builds candidate neighborhoods from cheap, high-recall buckets:

- exact normalized-title bucket
- informative-token buckets
- optional nearby length-band filtering inside token buckets

The purpose of blocking is to avoid obviously unrelated comparisons while still allowing reconstructed variants of the same underlying title to meet in at least one bucket.

### Stage 3: Verify

Only shortlisted pairs are sent to duplicate verification.

Verification continues to evaluate duplicate reasons through `_duplicate_reasons()`, but with one important role separation:

- anchor signals are sufficient to justify duplicate grouping
- supporting signals strengthen or explain a match after anchor evidence is present

Expected anchor signals in this pass:

- exact normalized-title collision
- substring or similarity-backed metadata/title proximity from the current resolver heuristics

Expected supporting signal in this pass:

- shared launcher ancestry

This preserves launcher ancestry in surfaced reasoning without letting a broad launcher like `Steam` or `Battle.net` make unrelated reconstructed titles look duplicate by itself.

### Stage 4: Group And Rank

Verified duplicate pairs are merged into candidate groups. Primary-title selection remains unchanged:

- higher title confidence first
- longer normalized canonical label preferred
- lexical tiebreaker last

The emitted `DuplicateCandidate` objects keep the current shape and downstream compatibility.

## Data Structures

The implementation should introduce small internal resolver helpers only as needed:

- a fingerprint dataclass or equivalent immutable record
- bucket maps keyed by normalized title and informative token
- a deterministic pair set keyed by ordered title ids or title indexes
- a group-building structure for verified adjacency

No new persisted schema is required for this pass.

## Algorithm Outline

1. Build fingerprints for all resolved titles.
2. Populate exact-normalized and token buckets.
3. Generate candidate pairs from each bucket, deduplicated through one pair set.
4. Optionally discard obviously weak pairs before deeper verification when no anchor condition is possible.
5. Run `_duplicate_reasons()` only for shortlisted pairs.
6. Keep only verified pairs.
7. Merge verified pairs into duplicate groups.
8. Rank each group's canonical primary title with the existing selection logic.
9. Emit stable `DuplicateCandidate` objects.

## Correctness Rules

The optimization must preserve these rules:

- exact normalized-title collisions still surface as duplicate candidates
- reconstructed variants of the same underlying title still surface as duplicate candidates
- unrelated reconstructed titles must not become duplicate candidates merely because they share a launcher
- duplicate reasons remain explainable and user-visible
- ambiguous or weak cases should remain ambiguous instead of being forced into duplicates for cosmetic completeness

## Testing Strategy

Implementation should follow test-driven development.

### Correctness Regressions

Add or extend resolver tests to assert:

- exact normalized collisions still surface
- near-variant reconstructed titles still surface
- higher-confidence titles still win as the primary candidate
- shared launcher alone is not enough to create a duplicate candidate

### Scale-Oriented Verification Tests

Add tests that instrument verification fanout rather than relying on unstable wall-clock timing.

The test seam should demonstrate that:

- large unrelated title sets do not cause broad pairwise verification
- candidate verification count grows with plausible duplicate neighborhoods rather than the full cartesian pair set

### Compatibility Coverage

Existing duplicate-candidate rendering and reporting tests should continue to pass without output-shape changes.

## Risks And Mitigations

### Risk: False Negatives From Overly Narrow Buckets

Mitigation:
- keep blocking high-recall
- use both exact-normalized and token buckets
- preserve verification semantics for shortlisted pairs
- retain existing fixtures that exercise ambiguous duplicate cases

### Risk: False Positives From Overweighting Launcher Signals

Mitigation:
- treat launcher ancestry as supporting rather than standalone duplicate proof
- add explicit regression coverage for unrelated titles sharing the same launcher

### Risk: Downstream Churn

Mitigation:
- keep `DuplicateCandidate` unchanged
- constrain changes to resolver internals and tests for this pass

## Acceptance Criteria

- duplicate detection no longer performs a naive full pairwise scan across all resolved titles
- duplicate-candidate correctness remains equivalent or better on existing reconstruction tests
- large unrelated title sets trigger materially less verification fanout than the current implementation
- no documented reconstruction or lineage behavior is removed or weakened
- downstream report/export/render flows continue to consume the same duplicate-candidate contract

## Follow-Through

Once this design is approved and committed, the implementation plan should focus on:

1. failing resolver tests for correctness and verification fanout
2. resolver-internal `bucket + verify` implementation
3. validation against the full test suite
4. closing the deferred issue note if the acceptance criteria are met
