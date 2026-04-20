# Duplicate Detection Performance Follow-Up

Date: `2026-04-19`

Status: completed

Related code:

- `playtrace/classify/resolver.py`
- `TitleResolver._duplicate_candidates()`

Related PR:

- `#5 Improve reconstruction heuristics and lineage surfaces`

## Summary

The original duplicate-candidate pass in `TitleResolver._duplicate_candidates()` performed a pairwise comparison across the full `titles` list. That was an `O(N^2)` walk over resolved titles.

That behavior was acceptable for small and moderate title sets, but it was the remaining known scalability outlier from PR `#5`. The follow-up is now complete.

## Why This Is A Follow-Up

- The current code is functionally correct.
- The open review note is about scaling, not a known wrong result on the current branch.
- The reconstruction/lineage rollout already landed and was validated end-to-end.
- Optimizing this path should be done deliberately so duplicate reasoning quality does not regress while chasing lower asymptotic cost.

## Previous Behavior

`_duplicate_candidates()` previously:

1. walks titles in order
2. compares each title to every later title
3. calls `_duplicate_reasons()` for each pair
4. groups matches and selects a primary title by confidence and canonical-title quality

This produced good duplicate reasoning, but the nested scan could dominate runtime as title counts grow toward the upper limits used elsewhere in the system.

## Resolution

- Completed on `2026-04-20`.
- `TitleResolver` now builds resolver-local duplicate fingerprints and uses bucketed candidate-pair generation before verification.
- Duplicate verification still relies on title-based anchor evidence, while shared launcher ancestry remains surfaced as supporting reasoning only.
- Verified duplicate edges are now merged through deterministic connected components before rebuilding `DuplicateCandidate` output, preserving the downstream contract.
- Validation for the shipped pass:
  - `uv run pytest tests/test_title_resolution.py -q` -> `16 passed`
  - `uv run pytest tests/test_title_resolution.py tests/test_export_service.py tests/test_rebuild_service.py tests/test_store_schema.py -q` -> `42 passed`
  - `uv run pytest -q` -> `185 passed`

## Shipped Direction

The shipped pass kept the current duplicate-quality behavior while reducing the number of expensive pairwise comparisons.

Implemented direction:

- bucket titles by exact normalized form and informative title tokens before similarity checks
- reduce verification fanout by comparing only blocked candidate neighborhoods instead of the full resolved-title cartesian set
- preserve the existing duplicate reasons and primary-title selection behavior
- prevent launcher-only matches from surfacing duplicate candidates without title-based anchor evidence

## Acceptance Criteria

- duplicate detection no longer performs a naive full pairwise scan across all resolved titles
- duplicate reasoning remains equivalent or better for existing reconstruction tests
- large-title-set behavior is measurably better than the current implementation
- no documented reconstruction or lineage behavior is removed or weakened
