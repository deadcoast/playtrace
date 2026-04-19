# Duplicate Detection Performance Follow-Up

Date: `2026-04-19`

Status: completed

Related code:

- `playtrace/classify/resolver.py`
- `TitleResolver._duplicate_candidates()`

Related PR:

- `#5 Improve reconstruction heuristics and lineage surfaces`

## Summary

The current duplicate-candidate pass in `TitleResolver._duplicate_candidates()` performs a pairwise comparison across the full `titles` list. This is an `O(N^2)` walk over resolved titles.

That behavior is acceptable for small and moderate title sets, but it is the remaining known scalability outlier from PR `#5`. The current implementation was kept because the correctness and lineage review items were higher priority, and this optimization needs its own follow-up instead of being changed blindly during review cleanup.

## Why This Is A Follow-Up

- The current code is functionally correct.
- The open review note is about scaling, not a known wrong result on the current branch.
- The reconstruction/lineage rollout already landed and was validated end-to-end.
- Optimizing this path should be done deliberately so duplicate reasoning quality does not regress while chasing lower asymptotic cost.

## Current Behavior

`_duplicate_candidates()` currently:

1. walks titles in order
2. compares each title to every later title
3. calls `_duplicate_reasons()` for each pair
4. groups matches and selects a primary title by confidence and canonical-title quality

This produces good duplicate reasoning, but the nested scan can dominate runtime as title counts grow toward the upper limits used elsewhere in the system.

## Risk

- slower rebuild preview on larger databases
- slower duplicate reporting surfaces that depend on resolver output
- unnecessary CPU work when many titles are obviously unrelated

## Desired Direction

The next pass should keep the current duplicate-quality behavior while reducing the number of expensive pairwise comparisons.

Candidate directions:

- bucket titles by normalized-title prefix or exact normalized form before similarity checks
- short-circuit obvious non-matches before `SequenceMatcher` work
- use launcher and classification constraints to avoid cross-bucket comparisons
- preserve the current duplicate reasons and primary-title selection behavior

## Acceptance Criteria

- duplicate detection no longer performs a naive full pairwise scan across all resolved titles
- duplicate reasoning remains equivalent or better for existing reconstruction tests
- large-title-set behavior is measurably better than the current implementation
- no documented reconstruction or lineage behavior is removed or weakened

## Resolution

Completed on `2026-04-19`.

- duplicate candidate generation now uses resolver-local blocking plus verification instead of a full forward pairwise scan
- shared launcher ancestry remains part of surfaced duplicate reasoning, but only as supporting evidence after a title-similarity anchor exists
- existing `DuplicateCandidate` output contracts were preserved for downstream report, export, and rebuild consumers
