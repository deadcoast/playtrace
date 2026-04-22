# Duplicate Detection Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the naive `O(N^2)` duplicate-candidate scan in `TitleResolver` with a bucket-and-verify flow that preserves reconstruction-oriented duplicate reasoning and the existing `DuplicateCandidate` output contract.

**Architecture:** Keep the work inside `playtrace/classify/resolver.py`. Add resolver-local title fingerprints and blocking buckets to generate a small verified pair set, then build duplicate groups from verified edges while preserving the current primary-title selection logic and downstream output shape.

**Tech Stack:** Python 3.12, pytest, existing `TitleResolver` heuristics, Rich/report consumers unchanged

---

## File Map

- Modify: `playtrace/classify/resolver.py`
  - Add internal fingerprint/blocking helpers.
  - Replace the full forward scan in `_duplicate_candidates()`.
  - Tighten duplicate verification so launcher ancestry is supporting evidence, not standalone duplicate proof.
- Modify: `tests/test_title_resolution.py`
  - Add correctness regressions for duplicate semantics.
  - Add a verification-fanout test using an instrumented resolver seam.
- Modify: `docs/TODO.md`
  - Mark the remaining duplicate-detection follow-up complete when the implementation is validated.
- Modify: `docs/CHANGELOG.md`
  - Record the resolver optimization and duplicate-proof tightening.
- Modify: `docs/archive/notes/2026-04-19-duplicate-detection-performance.md`
  - Update the deferred note to reflect completion and reference the shipped behavior.

## Task 1: Add Failing Resolver Correctness Tests

**Files:**
- Modify: `tests/test_title_resolution.py`
- Test: `tests/test_title_resolution.py`

- [ ] **Step 1: Add a regression test that launcher ancestry alone is not enough**

```python
def test_duplicate_candidates_require_more_than_shared_launcher() -> None:
    left = ResolvedTitle(
        title_id="title:alpha",
        title="Alpha Protocol",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:alpha",
    )
    right = ResolvedTitle(
        title_id="title:beta",
        title="Balatro",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:beta",
    )

    assert TitleResolver()._duplicate_candidates([left, right]) == []
```

- [ ] **Step 2: Add a regression test that near-variant reconstructed titles still surface**

```python
def test_duplicate_candidates_keep_reconstructed_variants() -> None:
    left = ResolvedTitle(
        title_id="title:elden-ring",
        title="ELDEN RING",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.HIGH,
        launcher="Steam",
        primary_exe_id="exe:1",
    )
    right = ResolvedTitle(
        title_id="title:elden-ring-deluxe",
        title="Elden Ring Deluxe",
        classification=Classification.GAME,
        classification_confidence=ConfidenceLevel.HIGH,
        title_confidence=ConfidenceLevel.MEDIUM,
        launcher="Steam",
        primary_exe_id="exe:2",
    )

    candidates = TitleResolver()._duplicate_candidates([left, right])

    assert len(candidates) == 1
    assert candidates[0].primary_title == "ELDEN RING"
```

- [ ] **Step 3: Run the targeted correctness tests and confirm they fail on current main**

Run:

```bash
uv run pytest tests/test_title_resolution.py::test_duplicate_candidates_require_more_than_shared_launcher tests/test_title_resolution.py::test_duplicate_candidates_keep_reconstructed_variants -q
```

Expected:
- the shared-launcher test fails because `_duplicate_reasons()` currently treats launcher ancestry as sufficient
- the near-variant test still passes or remains stable; if it fails, capture the exact mismatch before implementation

## Task 2: Add Failing Verification-Fanout Test

**Files:**
- Modify: `tests/test_title_resolution.py`
- Test: `tests/test_title_resolution.py`

- [ ] **Step 1: Add an instrumented resolver subclass that counts pair verification calls**

```python
class CountingTitleResolver(TitleResolver):
    def __init__(self) -> None:
        super().__init__()
        self.duplicate_reason_calls = 0

    def _duplicate_reasons(self, left: ResolvedTitle, right: ResolvedTitle) -> list[str]:
        self.duplicate_reason_calls += 1
        return super()._duplicate_reasons(left, right)
```

- [ ] **Step 2: Add a large unrelated-title test that proves the search space is reduced**

```python
def test_duplicate_candidates_reduce_verification_fanout_for_unrelated_titles() -> None:
    titles = [
        ResolvedTitle(
            title_id=f"title:{index}",
            title=f"Distinct Adventure {index}",
            classification=Classification.GAME,
            classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH,
            launcher=None,
            primary_exe_id=f"exe:{index}",
        )
        for index in range(40)
    ]
    resolver = CountingTitleResolver()

    candidates = resolver._duplicate_candidates(titles)

    assert candidates == []
    assert resolver.duplicate_reason_calls < 100
```

- [ ] **Step 3: Run the fanout test and confirm it fails on current main**

Run:

```bash
uv run pytest tests/test_title_resolution.py::test_duplicate_candidates_reduce_verification_fanout_for_unrelated_titles -q
```

Expected:
- FAIL because the current implementation performs the full pairwise walk, giving `780` verification calls for `40` unrelated titles

## Task 3: Implement Resolver Fingerprints And Buckets

**Files:**
- Modify: `playtrace/classify/resolver.py`
- Test: `tests/test_title_resolution.py`

- [ ] **Step 1: Add a small internal fingerprint record**

Add an internal dataclass or equivalent immutable helper near `ResolvedTitle`:

```python
@dataclass(slots=True, frozen=True)
class _DuplicateFingerprint:
    index: int
    title_id: str
    normalized_title: str
    informative_tokens: tuple[str, ...]
    length_band: int
    launcher_key: str | None
```

- [ ] **Step 2: Add helper methods for duplicate blocking**

Implement focused helpers in `TitleResolver`:

```python
def _duplicate_fingerprint(self, index: int, title: ResolvedTitle) -> _DuplicateFingerprint: ...
def _informative_duplicate_tokens(self, title: str) -> tuple[str, ...]: ...
def _duplicate_candidate_pairs(
    self,
    titles: list[ResolvedTitle],
) -> set[tuple[int, int]]: ...
```

Guidance:
- normalize once per title
- strip empty and low-signal tokens
- bucket by exact normalized title and by informative token
- optionally reject clearly distant length bands inside token buckets
- keep pair generation deterministic with ordered `(left_index, right_index)` tuples

- [ ] **Step 3: Replace the naive pairwise walk in `_duplicate_candidates()` with blocked candidate pairs**

Target shape:

```python
candidate_pairs = self._duplicate_candidate_pairs(titles)
for left_index, right_index in sorted(candidate_pairs):
    left = titles[left_index]
    right = titles[right_index]
    duplicate_reasons = self._duplicate_reasons(left, right)
```

- [ ] **Step 4: Run the three targeted tests**

Run:

```bash
uv run pytest tests/test_title_resolution.py::test_duplicate_candidates_require_more_than_shared_launcher tests/test_title_resolution.py::test_duplicate_candidates_keep_reconstructed_variants tests/test_title_resolution.py::test_duplicate_candidates_reduce_verification_fanout_for_unrelated_titles -q
```

Expected:
- the fanout test still fails until duplicate-proof tightening and grouping are complete
- the bucketed candidate generation should already reduce the verification count materially

## Task 4: Tighten Duplicate Proof And Build Groups From Verified Edges

**Files:**
- Modify: `playtrace/classify/resolver.py`
- Test: `tests/test_title_resolution.py`

- [ ] **Step 1: Separate anchor reasons from supporting reasons inside `_duplicate_reasons()`**

Refactor `_duplicate_reasons()` so it only returns non-empty output when an anchor signal exists:

```python
anchor_reasons: list[str] = []
supporting_reasons: list[str] = []

if normalized_left == normalized_right:
    anchor_reasons.extend(["normalized title collision", "metadata-backed title similarity"])
elif normalized_left in normalized_right or normalized_right in normalized_left:
    anchor_reasons.append("metadata-backed title similarity")
elif title_similarity(left.title, right.title) >= 0.70:
    anchor_reasons.append("metadata-backed title similarity")

if left.launcher and right.launcher and left.launcher == right.launcher:
    supporting_reasons.append("shared launcher ancestry")

return sorted(set(anchor_reasons + supporting_reasons)) if anchor_reasons else []
```

- [ ] **Step 2: Build duplicate groups from verified adjacency rather than first-title forward scans**

Implement a small helper such as:

```python
def _duplicate_groups(
    self,
    titles: list[ResolvedTitle],
    verified_pairs: set[tuple[int, int]],
) -> list[list[ResolvedTitle]]: ...
```

Guidance:
- treat verified pairs as an undirected graph
- compute connected components deterministically
- rank each component with the existing primary-title sort

- [ ] **Step 3: Rebuild `DuplicateCandidate` output from verified groups**

Keep the current output contract:

```python
DuplicateCandidate(
    primary_title_id=primary.title_id,
    primary_title=primary.title,
    related_title_ids=[title.title_id for title in related],
    related_titles=[title.title for title in related],
    reasons=sorted(collected_reasons),
)
```

- [ ] **Step 4: Run the targeted resolver test file**

Run:

```bash
uv run pytest tests/test_title_resolution.py -q
```

Expected:
- PASS for all resolver/title-resolution tests

- [ ] **Step 5: Commit the resolver implementation**

```bash
git add playtrace/classify/resolver.py tests/test_title_resolution.py
git commit -m "Optimize duplicate candidate detection"
```

## Task 5: Validate Broader Compatibility

**Files:**
- Modify: none expected unless regression fixes are required
- Test: `tests/test_title_resolution.py`
- Test: `tests/test_export_service.py`
- Test: `tests/test_rebuild_service.py`
- Test: `tests/test_store_schema.py`

- [ ] **Step 1: Run the focused downstream suite that consumes duplicate candidates**

Run:

```bash
uv run pytest tests/test_title_resolution.py tests/test_export_service.py tests/test_rebuild_service.py tests/test_store_schema.py -q
```

Expected:
- PASS with no `DuplicateCandidate` contract regressions

- [ ] **Step 2: Run the full suite**

Run:

```bash
uv run pytest -q
```

Expected:
- PASS for the full repository test suite

## Task 6: Update Completion Docs

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/archive/notes/2026-04-19-duplicate-detection-performance.md`

- [ ] **Step 1: Mark the follow-up complete in `docs/TODO.md`**

Update:

```markdown
- [x] Optimize duplicate-candidate detection in `TitleResolver` to remove the current `O(N^2)` full pairwise scan on large title sets.
```

- [ ] **Step 2: Add a concise shipped note to `docs/CHANGELOG.md`**

Record:
- bucket-and-verify duplicate candidate generation in `TitleResolver`
- launcher ancestry moved to supporting evidence
- verification fanout reduced for large unrelated title sets

- [ ] **Step 3: Update the archived follow-up note to reflect resolution**

Add a completion block such as:

```markdown
## Resolution

Completed on `2026-04-19`.

- duplicate candidate generation now uses resolver-local blocking plus verification
- naive full pairwise verification was removed
- existing duplicate-candidate output contracts were preserved
```

- [ ] **Step 4: Commit the documentation updates**

```bash
git add docs/TODO.md docs/CHANGELOG.md docs/archive/notes/2026-04-19-duplicate-detection-performance.md
git commit -m "Document duplicate detection optimization"
```

## Task 7: Final Verification And Integration

**Files:**
- Modify: none expected

- [ ] **Step 1: Check the final worktree state**

Run:

```bash
git status --short
```

Expected:
- no unexpected modified files

- [ ] **Step 2: Inspect the commit series**

Run:

```bash
git log --oneline -n 5
```

Expected:
- one implementation commit
- one documentation commit
- earlier spec and plan commits preserved

- [ ] **Step 3: Push the branch if this plan is executed on a branch or reconcile to `main` per user instruction**

Run one of:

```bash
git push
```

or:

```bash
git push origin HEAD:main
```

Expected:
- remote updated with the duplicate-detection completion work
