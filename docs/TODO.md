# TODO

This file tracks the current recovery status. Completed rollout items are also summarized in `docs/CHANGELOG.md`.

## Recovery Status

- [x] Recover `scan` into a rendered command with source-by-source status and a final summary.
- [x] Add `playtrace me` as a stored-data identity dashboard with optional `--refresh`.
- [x] Rebuild `report`, `titles`, and `sessions` on shared snapshot loaders instead of stubs or placeholders.
- [x] Turn `doctor` into an environment and persisted-data audit with explicit remediation guidance.
- [x] Surface suspected duplicate titles and support aggressive `playtrace map --auto` merging.
- [x] Reintegrate `inspect`, `sources`, and `export` with the recovered truth layer.
- [x] Raise the baseline visual structure across `scan`, `me`, `report`, and `doctor`.

## Remaining Follow-Up

- [x] Replace the full duplicate-verification scan with conservative indexed candidates and direct-primary verification. Worst-case work remains quadratic; see `docs/archive/notes/2026-04-19-duplicate-detection-performance.md`.
- [ ] Resolve the pre-existing date-sensitive full-suite failure and reconcile issue #6 / superseded PRs #7 and #9 after publication verification.
- [x] Refine real-world title and session reconstruction heuristics on larger live datasets.
- [x] Expand the polished visual language further across `inspect`, `sources`, and `export`.

## Validation Note

- [x] `2026-04-18`: Reconstruction/lineage follow-up validated in the isolated worktree with focused reconstruction matrix `94 passed`, full suite `168 passed`, and hands-on command checks for `scan --rebuild`, `doctor --repair`, `inspect`, `sources`, and export scopes recorded in `docs/VALTEST.md`.
