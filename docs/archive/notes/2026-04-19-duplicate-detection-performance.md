# Duplicate Detection Performance Follow-Up

Date: `2026-04-19`

Status: implementation reconciled; full-suite follow-up remains

Related code:

- `playtrace/classify/resolver.py`
- `TitleResolver._duplicate_candidates()`

Related PR:

- `#5 Improve reconstruction heuristics and lineage surfaces`

## Summary

The original duplicate-candidate pass in `TitleResolver._duplicate_candidates()` performs a pairwise comparison across the full `titles` list. This is an `O(N^2)` walk over resolved titles.

That behavior is acceptable for small and moderate title sets, but it is the remaining known scalability outlier from PR `#5`. The current implementation was kept because the correctness and lineage review items were higher priority, and this optimization needs its own follow-up instead of being changed blindly during review cleanup.

## Why This Is A Follow-Up

- The current code is functionally correct.
- The open review note is about scaling, not a known wrong result on the current branch.
- The reconstruction/lineage rollout already landed and was validated end-to-end.
- Optimizing this path should be done deliberately so duplicate reasoning quality does not regress while chasing lower asymptotic cost.

## Current Behavior

`_duplicate_candidates()` originally:

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


## Reconciliation (2026-10-03)

The checked TODO on `main` at `01b714a67c60bd7c6fd105a2e616430508dfae32`
was premature: its resolver still used the original forward pairwise scan.
Issue #6 and PRs #7/#9 remained open at review time.

This change retains PR #9's direct-primary grouping and supporting-launcher
semantics, while replacing its candidate blocker. Comparing final PR snapshots
revealed remaining omissions despite earlier review replies:

- PR #7 (`2eaad73ce2be1a6a4d788b04a3cc6d288ef56944`) can emit reversed pair
  indexes, losing a verified `EldenRingDeluxe` / `EldenRing` match. Its grouping
  still scans all pairs, and its connected components can merge titles without
  direct evidence against the selected primary.
- PR #9 (`826204be1928a412d271b8d1b1318aaa868c8e9f`) misses short substrings
  such as `A` / `A Deluxe` and fuzzy variants with different head/tail keys.
  Its bucket-size cutoff also removes valid fuzzy matches when other titles
  are added. Numbered near-identical titles are not valid unrelated-title
  performance fixtures under the existing similarity threshold.

### New candidate index

Normalize titles once for indexing. Process longest first and retrieve previous
longer titles from character postings for short queries and bigram postings for
queries longer than ten normalized characters. Index every title under both
kinds of posting. Containment bypasses the length and character-overlap gates;
other pairs use integer upper bounds before the existing similarity verifier.
Candidates are streamed per query rather than retained as a global pair set.

For strings of total length S and M characters matched by SequenceMatcher,
there are at most S - 2M + 1 nonempty matching runs. A ratio of at least 0.70
implies 2M/S >= 0.70. If S > 20, M > S - 2M + 1, so at least one run contains
a shared bigram. Shorter queries use character postings instead, preserving
the boundary case `abcdefg` / `axbxcxdxexfxg` (ratio exactly 0.70, no bigram).
Substring matches necessarily share the shorter title's grams, even when the
length ratio is arbitrarily small. Ordered pair indexes retain the original
SequenceMatcher argument order.

### Scope and limits

The result shape and primary ranking remain unchanged. Launcher-only matches
are intentionally removed. Groups intentionally contain only direct matches
to their chosen primary, avoiding transitive-only automatic merges.

This is an expensive-verification reduction, not a universal subquadratic
algorithm. Short/common-character postings may still touch quadratic pairs;
genuinely dense duplicate graphs still require quadratic verified-edge storage.
No lossy bucket-size cap or global linear-time claim is made.

Validation and reproducible benchmark results are recorded in
`docs/duplicate-detection-validation.md`. Local verification does not close issue #6, merge either earlier PR,
or substitute for remote CI.
