# Duplicate-detection validation

Date: 2026-10-03

## Baseline and scope

Prepared against `deadcoast/playtrace` main commit
`01b714a67c60bd7c6fd105a2e616430508dfae32`.
The private repository was materialized through its authorized GitHub reader;
direct Git clone was unavailable. All 176 text files were fetched at that SHA.
The tracked binary `playtrace.db` was intentionally excluded from execution;
tests create their own temporary databases. No repository-specific `.agents/skills`
were present; `AGENTS.md` and development instructions were read.

PR #7 head: `2eaad73ce2be1a6a4d788b04a3cc6d288ef56944`.
PR #9 head: `826204be1928a412d271b8d1b1318aaa868c8e9f`.
The patch reconciles useful PR #9 behavior while replacing lossy blocking.
See the archived performance note for exact reproduced defects and the new
candidate-recall argument.

This report records the pre-publication validation snapshot. At that point no
push, PR update, merge, deployment, issue closure, or remote CI run had occurred.
The user subsequently authorized publishing the correction to `main`; remote
publication and CI results must be verified separately.

## Verification

Environment: Linux, Python 3.13.5 (matching `.python-version`), dependencies
from the committed `uv.lock`, pytest 9.1.1. Native Windows integration remains
outside this environment's coverage.

- Baseline `uv run pytest -q`: **183 passed, 2 skipped, 1 failed**.
- Final focused resolver/export/rebuild/schema/mapping suite: **57 passed**.
- Final `uv run pytest -q`: **196 passed, 2 skipped, 1 failed**.
- `uv build`: **passed**, producing source distribution and wheel.
- `uv run python -m playtrace --help`: **passed**.
- Python compilation of `playtrace`, `tests`, and `tools`: **passed**.
- `git diff --check`: **passed**.
- No project lint/type-check command is configured in `pyproject.toml`.

The unchanged failure is
`tests/test_command_config_integration.py::test_sessions_uses_config_days_when_cli_days_is_unset`.
Its “Recent Game” fixture is dated 2026-04-16, but its seven-day window uses the
current clock. It therefore fails on 2026-10-03 both before and after this patch.
A diagnostic run freezing `Database._utc_now` to 2026-04-18 passes (1 passed);
that diagnostic did not modify the repository. The real-clock full suite is
**not green** and the patch is not claimed merge-ready.

## Regression and independent review

Added 13 tests cover launcher-only false positives, supporting launcher reasons,
confidence-compatible primary grouping, direct-primary evidence, deterministic
nonoverlapping groups, empty/ASCII-normalized-empty/Unicode inputs, short titles,
long containment, dense buckets, reversed input ordering, threshold boundaries,
and pairwise-oracle comparisons on exhaustive short strings and seeded variants.
The boundary `abcdefg` / `axbxcxdxexfxg` has similarity exactly 0.70 but no shared
bigram, so the character-posting fallback is required.

A separate read-only review found no blocking correctness defects. Differential
checks over 126 exhaustive binary strings (lengths 1–6) in both orders and an
800-title randomized/edited corpus had zero missed accepted pairs, duplicate
yields, or unordered index pairs. The latter shortlisted 9,738 of 319,600 pairs
and retained all 6,604 verifier-accepted pairs. Review also confirmed the known
quadratic worst-case CPU and verified-edge-memory limits.

## Reproducible synthetic benchmark

Three repeats, median full `_duplicate_candidates` wall time, seed 42,
independent 24-character lowercase strings with no launcher. Baseline code is
loaded from the saved unmodified resolver. All runs produced zero duplicate
groups for both implementations.

| Titles | Baseline verifications | Indexed verifications | Baseline seconds | Indexed seconds | Speedup |
|---:|---:|---:|---:|---:|---:|
| 200 | 19,900 | 71 | 0.507809 | 0.024293 | 20.9x |
| 500 | 124,750 | 404 | 3.246983 | 0.138327 | 23.47x |
| 1000 | 499,500 | 1,559 | 12.795423 | 0.534869 | 23.92x |

These are synthetic CPU timings on one environment, not production-data claims.
Short/common-character titles may still enumerate quadratic candidate pairs;
genuinely similar titles still create dense verified graphs. There is no lossy
bucket cap and no blanket subquadratic complexity claim.

To reproduce from a checkout whose main still has the baseline:

```bash
git show main:playtrace/classify/resolver.py > /tmp/baseline_resolver.py
uv run python tools/benchmark_duplicate_detection.py --baseline /tmp/baseline_resolver.py
```

## Apply and next steps

The accompanying `playtrace-duplicate-detection.patch` applies to the baseline
above using `git apply --check` followed by `git apply`. Review the patch before
applying it to another revision. No commits are required by the artifact.

After publication, verify CI at the published commit,
resolve the pre-existing date-sensitive test before claiming a green full suite,
and reconcile issue #6 / obsolete PRs as separately authorized.
