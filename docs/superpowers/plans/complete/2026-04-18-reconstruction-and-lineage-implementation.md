# Playtrace Reconstruction and Lineage Follow-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve evidence-backed executable/title/session reconstruction on live datasets, add explicit previewed repair flows through `scan --rebuild` and `doctor --repair`, and upgrade `inspect`, `sources`, and `export` to render repaired lineage clearly.

**Architecture:** Keep persisted raw artifacts and evidence as the immutable base. Add a shared repair planner that computes rebuilt executables, titles, sessions, and before/after diffs without mutating until `--yes` is passed, then build a shared lineage snapshot layer for `inspect`, `sources`, and `export` on top of that repaired truth. Ordinary `scan` behavior stays intact, while explicit repair flows use the shared planner and richer diff rendering.

**Tech Stack:** Python 3.12, Typer, Rich, SQLite, pytest, existing `playtrace/classify`, `playtrace/merge`, `playtrace/services`, `playtrace/store`, `playtrace/render`, and config runtime/resolver layers

---

## File Structure

### New Files

- `playtrace/models/lineage.py`
  - Shared lineage dataclasses for resolved entity views, source contributions, ambiguity markers, and evidence reasoning used by `inspect`, `sources`, and `export`.
- `playtrace/models/repair.py`
  - Shared repair-preview and repair-result dataclasses for rebuild diffs, counts, and before/after summaries.
- `playtrace/services/rebuild.py`
  - Shared repair planner/applier for previewing and applying in-place rebuilds from persisted evidence plus mappings.
- `tests/support/__init__.py`
  - Marks the shared test-support directory as import-safe under the current test layout.
- `tests/support/reconstruction_cases.py`
  - Live-like duplicate-title, split-session, launcher-misattribution, and weak-evidence dataset builders reused across heuristic, repair, and lineage tests.
- `tests/test_rebuild_service.py`
  - Shared repair planner and apply-flow tests.
- `tests/test_lineage_service.py`
  - Shared lineage snapshot tests for repaired truth, ambiguity, and evidence reasoning.

### Modified Files

- `playtrace/classify/heuristics.py`
  - Replace the shallow runtime-only executable chooser with scored identity and primary-selection helpers.
- `playtrace/classify/resolver.py`
  - Add richer evidence-backed title resolution, duplicate reasoning, and ambiguity preservation while keeping manual overrides narrow and exceptional.
- `playtrace/merge/titles.py`
  - Persist canonical-title reasons, alternate labels, and richer duplicate hints into title aggregates.
- `playtrace/merge/sessions.py`
  - Tighten session reconstruction around repaired executable identity, launcher continuity, and ambiguity notes.
- `playtrace/store/db.py`
  - Expose the data needed for repair planning, compare current derived state to proposed rebuilt state, and apply rebuilt executables/titles/sessions through one shared path.
- `playtrace/models/title.py`
  - Extend aggregate notes or lineage fields enough to carry canonical-title explanations without inventing a parallel aggregate type.
- `playtrace/models/session.py`
  - Extend notes usage for repaired-session explanations and ambiguity markers.
- `playtrace/services/scanner.py`
  - Keep ordinary scan behavior, but add explicit `--rebuild` preview/apply flow through the shared repair planner.
- `playtrace/services/doctor.py`
  - Add explicit `--repair` preview/apply flow and render repair output alongside audit findings.
- `playtrace/services/audit.py`
  - Surface stale reconstruction and repairable duplicate/session findings with repair-facing remediation language.
- `playtrace/services/inspector.py`
  - Replace ad hoc detail assembly with shared lineage snapshots and richer evidence reasoning.
- `playtrace/services/sources.py`
  - Replace raw evidence table assembly with shared lineage/provenance snapshots.
- `playtrace/services/exporter.py`
  - Export entity lineage, source lineage, and repair diff scopes from the shared lineage and repair models.
- `playtrace/render/source_views.py`
  - Upgrade `inspect` and `sources` rendering into stronger sectioned lineage/provenance views.
- `playtrace/render/repair_views.py`
  - Render repair previews and applied diffs for `scan --rebuild` and `doctor --repair`.
- `playtrace/cli/cmd_scan.py`
  - Add `--rebuild` and `--yes`.
- `playtrace/cli/cmd_doctor.py`
  - Add `--repair` and `--yes`.
- `playtrace/cli/cmd_export.py`
  - Add explicit export scope selection for lineage and repair diff exports.
- `playtrace/config/runtime.py`
  - Extend export runtime settings with scope; keep mutation flags explicit-only and out of config resolution.
- `playtrace/config/models.py`
  - Extend export config defaults with export scope if needed by the command surface.
- `playtrace/config/loader.py`
  - Parse any new export scope default cleanly.
- `playtrace/config/resolver.py`
  - Resolve new export scope defaults while leaving repair mutation flags explicit-only.
- `docs/config.example.toml`
  - Document any new export scope default and ensure example config still matches the real CLI surface.
- `tests/test_title_resolution.py`
  - Add live-like heuristic regression tests for canonical title choice, duplicate grouping, and weak-evidence ambiguity.
- `tests/test_merge_sessions.py`
  - Add live-like session reconstruction regressions driven by repaired identity.
- `tests/test_scan_service.py`
  - Cover `scan --rebuild` preview and `--yes` apply behavior.
- `tests/test_doctor.py`
  - Cover `doctor --repair` preview and `--yes` apply behavior.
- `tests/test_audit_service.py`
  - Cover repairable findings and no-op repair cases.
- `tests/test_inspect_view.py`
  - Cover lineage-rich inspect output and ambiguous-target handling.
- `tests/test_sources_command.py`
  - Cover provenance-rich sources output and cross-source conflicts.
- `tests/test_export_service.py`
  - Cover entity-lineage, source-lineage, and repair-diff export scopes.
- `tests/test_config_loader.py`
  - Cover any new export config field.
- `tests/test_config_resolver.py`
  - Cover export scope precedence.
- `tests/test_command_config_integration.py`
  - Cover config-backed export scope with CLI override.
- `docs/VALTEST.md`
  - Add rebuild preview/apply and improved lineage command validation.
- `docs/TODO.md`
  - Mark the two recovery follow-up items complete after implementation and validation.

### Existing Files to Read During Implementation

- `docs/superpowers/specs/2026-04-17-reconstruction-and-lineage-design.md`
- `playtrace/classify/heuristics.py`
- `playtrace/classify/resolver.py`
- `playtrace/merge/titles.py`
- `playtrace/merge/sessions.py`
- `playtrace/store/db.py`
- `playtrace/services/scanner.py`
- `playtrace/services/doctor.py`
- `playtrace/services/inspector.py`
- `playtrace/services/sources.py`
- `playtrace/services/exporter.py`
- `playtrace/render/source_views.py`
- `tests/test_title_resolution.py`
- `tests/test_merge_sessions.py`
- `tests/test_scan_service.py`
- `tests/test_doctor.py`
- `tests/test_inspect_view.py`
- `tests/test_sources_command.py`
- `tests/test_export_service.py`

## Task 1: Add Live-Like Reconstruction Fixtures and the First Failing Heuristic Regressions

**Files:**
- Create: `tests/support/__init__.py`
- Create: `tests/support/reconstruction_cases.py`
- Modify: `tests/test_title_resolution.py`
- Modify: `tests/test_merge_sessions.py`

- [ ] **Step 1: Write the failing title and session regression tests using live-like cases**

```python
from tests.support.reconstruction_cases import (
    duplicate_title_case,
    split_session_case,
    weak_title_case,
)


def test_title_resolver_prefers_evidence_backed_game_binary_over_launcher_labels() -> None:
    case = duplicate_title_case()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert [title.title for title in result.titles] == ["ELDEN RING"]
    assert result.duplicate_candidates == []


def test_session_merger_keeps_launcher_child_continuity_in_one_session() -> None:
    case = split_session_case()

    sessions = SessionMerger().build_sessions(case.evidence)

    assert len(sessions) == 1
    assert sessions[0].confidence is RuntimeConfidence.EXACT


def test_title_resolver_preserves_ambiguity_when_evidence_is_too_weak() -> None:
    case = weak_title_case()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert result.titles[0].title_confidence is ConfidenceLevel.UNKNOWN
    assert "ambiguous" in " ".join(result.titles[0].notes).lower()
```

- [ ] **Step 2: Run the regression tests and confirm they fail on the current shallow heuristics**

Run: `uv run pytest tests/test_title_resolution.py tests/test_merge_sessions.py -q`
Expected: FAIL because the current resolver groups by first available title strings and the session merger does not carry richer launcher continuity or ambiguity notes.

- [ ] **Step 3: Add the shared live-like case builders**

```python
@dataclass(slots=True)
class ReconstructionCase:
    executables: list[ExecutableIdentity]
    sessions: list[SessionRecord]
    evidence: list[EvidenceRecord]


def duplicate_title_case() -> ReconstructionCase:
    ...


def duplicate_title_case_with_remaining_ambiguity() -> ReconstructionCase:
    ...


def split_session_case() -> ReconstructionCase:
    ...


def weak_title_case() -> ReconstructionCase:
    ...
```

- [ ] **Step 4: Re-run the tests to confirm the helper imports work and the failures are now behavioral**

Run: `uv run pytest tests/test_title_resolution.py tests/test_merge_sessions.py -q`
Expected: FAIL on assertions, not on missing imports.

- [ ] **Step 5: Commit the fixtures and failing regressions**

```bash
git add tests/support/__init__.py tests/support/reconstruction_cases.py tests/test_title_resolution.py tests/test_merge_sessions.py
git commit -m "test: add live reconstruction regressions"
```

## Task 2: Implement Evidence Ranking, Canonical Title Selection, and Duplicate Reasoning

**Files:**
- Modify: `playtrace/classify/heuristics.py`
- Modify: `playtrace/classify/resolver.py`
- Modify: `playtrace/merge/titles.py`
- Modify: `playtrace/models/title.py`
- Test: `tests/test_title_resolution.py`

- [ ] **Step 1: Extend the failing tests to pin duplicate reasoning and alternate-label retention**

```python
def test_duplicate_candidates_include_lineage_reasoning() -> None:
    case = duplicate_title_case_with_remaining_ambiguity()

    result = TitleResolver().resolve(case.executables, case.sessions, mappings=[])

    assert result.duplicate_candidates[0].reasons
    assert "metadata" in " ".join(result.duplicate_candidates[0].reasons).lower()
```

- [ ] **Step 2: Run the title tests and confirm the current resolver still lacks these behaviors**

Run: `uv run pytest tests/test_title_resolution.py -q`
Expected: FAIL because `choose_primary_executable()` is runtime-weighted only and duplicate reasons are hardcoded.

- [ ] **Step 3: Implement scored executable-primary helpers and richer title-resolution output**

```python
def executable_identity_score(executable: ExecutableIdentity, sessions: list[SessionRecord]) -> int:
    score = total_runtime_by_executable(sessions).get(executable.exe_id, 0)
    if executable.sha1:
        score += 50_000
    if executable.product_name:
        score += 25_000
    if executable.signer:
        score += 10_000
    ...
    return score


@dataclass(slots=True)
class ResolvedTitle:
    ...
    alternate_titles: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Thread notes, alternate labels, and evidence-backed duplicate reasons into title aggregates**

```python
title.notes.extend(resolved.notes)
title.tags.extend(sorted(set(resolved.alternate_titles)))
```

- [ ] **Step 5: Re-run the title tests**

Run: `uv run pytest tests/test_title_resolution.py -q`
Expected: PASS with a single canonical title for the live duplicate case, preserved ambiguity for weak evidence, and richer duplicate reasons.

- [ ] **Step 6: Commit the heuristic/title-resolution improvements**

```bash
git add playtrace/classify/heuristics.py playtrace/classify/resolver.py playtrace/merge/titles.py playtrace/models/title.py tests/test_title_resolution.py
git commit -m "feat: improve title lineage heuristics"
```

## Task 3: Implement Session Reconstruction from Repaired Identity

**Files:**
- Modify: `playtrace/merge/sessions.py`
- Modify: `playtrace/models/session.py`
- Test: `tests/test_merge_sessions.py`

- [ ] **Step 1: Add failing session tests for launcher continuity, split windows, and residual ambiguity**

```python
def test_session_merger_emits_ambiguity_note_when_exact_pairing_is_missing() -> None:
    case = weak_title_case()

    sessions = SessionMerger().build_sessions(case.evidence)

    assert sessions[0].confidence is RuntimeConfidence.UNKNOWN
    assert any("missing exit" in note.lower() for note in sessions[0].notes)
```

- [ ] **Step 2: Run the session tests and confirm the current merger is still start/exit-only**

Run: `uv run pytest tests/test_merge_sessions.py -q`
Expected: FAIL because session notes and richer continuity handling do not exist yet.

- [ ] **Step 3: Implement repaired-identity session merging and notes**

```python
def _continuity_key(self, record: EvidenceRecord) -> tuple[str, str | None, str | None]:
    return self.normalizer.build_key(record), self._string_value(record, "user_sid"), self._string_value(record, "parent_pid")


def _build_partial_session(self, start: EvidenceRecord, note: str) -> SessionRecord:
    ...
    notes=[note],
```

- [ ] **Step 4: Re-run the session tests**

Run: `uv run pytest tests/test_merge_sessions.py -q`
Expected: PASS with launcher-child continuity handled more cleanly and ambiguity notes preserved when evidence is incomplete.

- [ ] **Step 5: Commit the session reconstruction changes**

```bash
git add playtrace/merge/sessions.py playtrace/models/session.py tests/test_merge_sessions.py
git commit -m "feat: improve session reconstruction lineage"
```

## Task 4: Add Shared Repair Models and Failing Preview/Apply Tests

**Files:**
- Create: `playtrace/models/repair.py`
- Create: `tests/test_rebuild_service.py`
- Modify: `tests/test_scan_service.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_audit_service.py`

- [ ] **Step 1: Write failing tests for repair preview, no-op preview, and `--yes`-gated apply**

```python
def test_rebuild_service_previews_changes_without_mutating_database(tmp_path: Path) -> None:
    db = seeded_duplicate_database(tmp_path)

    preview = RebuildService().plan(db.path)

    assert preview.title_changes
    assert Database(db.path).count_duplicate_title_groups() == 1


def test_rebuild_service_apply_requires_explicit_confirmation(tmp_path: Path) -> None:
    db = seeded_duplicate_database(tmp_path)

    with pytest.raises(PermissionError):
        RebuildService().apply(db.path, preview=RebuildService().plan(db.path), confirmed=False)
```

- [ ] **Step 2: Run the repair tests and confirm the shared planner does not exist yet**

Run: `uv run pytest tests/test_rebuild_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_audit_service.py -q`
Expected: FAIL because `RebuildService` and repair-aware scan/doctor flows do not exist.

- [ ] **Step 3: Add the repair diff dataclasses**

```python
@dataclass(slots=True)
class RepairCounts:
    merged_titles: int = 0
    changed_titles: int = 0
    changed_sessions: int = 0
    remaining_duplicate_groups: int = 0


@dataclass(slots=True)
class RepairPreview:
    counts: RepairCounts
    title_changes: list[str] = field(default_factory=list)
    session_changes: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Re-run the repair tests to confirm they now fail on behavior, not imports**

Run: `uv run pytest tests/test_rebuild_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_audit_service.py -q`
Expected: FAIL on missing behavior or assertions only.

- [ ] **Step 5: Commit the repair-model scaffolding**

```bash
git add playtrace/models/repair.py tests/test_rebuild_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_audit_service.py
git commit -m "test: add repair preview regressions"
```

## Task 5: Implement the Shared Repair Planner and Integrate `scan --rebuild` / `doctor --repair`

**Files:**
- Create: `playtrace/services/rebuild.py`
- Create: `playtrace/render/repair_views.py`
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/services/scanner.py`
- Modify: `playtrace/services/doctor.py`
- Modify: `playtrace/services/audit.py`
- Modify: `playtrace/cli/cmd_scan.py`
- Modify: `playtrace/cli/cmd_doctor.py`
- Test: `tests/test_rebuild_service.py`
- Test: `tests/test_scan_service.py`
- Test: `tests/test_doctor.py`
- Test: `tests/test_audit_service.py`

- [ ] **Step 1: Implement the shared repair planner and applier**

```python
class RebuildService:
    def plan(self, db_path: Path, settings: ReconstructionSettings | None = None) -> RepairPreview:
        current = self._load_current_state(db)
        proposed = self._build_proposed_state(db, settings)
        return self._diff(current=current, proposed=proposed)

    def apply(self, db_path: Path, *, preview: RepairPreview, confirmed: bool) -> RepairPreview:
        if not confirmed:
            raise PermissionError("Repair apply requires --yes.")
        self._write_proposed_state(...)
        return preview
```

- [ ] **Step 2: Thread explicit request-only repair flags through scan and doctor**

```python
@app.command("scan")
def scan(..., rebuild: bool = typer.Option(False, "--rebuild"), yes: bool = typer.Option(False, "--yes")) -> None:
    ...
```

- [ ] **Step 3: Render preview-first output for repair flows**

```python
if request.rebuild:
    preview = self.rebuild_service.plan(...)
    render_repair_preview(console, theme, preview)
    if request.yes:
        self.rebuild_service.apply(..., preview=preview, confirmed=True)
```

- [ ] **Step 4: Re-run the repair and command tests**

Run: `uv run pytest tests/test_rebuild_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_audit_service.py -q`
Expected: PASS with preview-only behavior by default, explicit apply only with `--yes`, and truthful no-op repair messaging.

- [ ] **Step 5: Commit the repair flows**

```bash
git add playtrace/services/rebuild.py playtrace/render/repair_views.py playtrace/store/db.py playtrace/services/scanner.py playtrace/services/doctor.py playtrace/services/audit.py playtrace/cli/cmd_scan.py playtrace/cli/cmd_doctor.py tests/test_rebuild_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_audit_service.py
git commit -m "feat: add explicit repair preview flows"
```

## Task 6: Add Shared Lineage Models and Failing Snapshot Tests

**Files:**
- Create: `playtrace/models/lineage.py`
- Create: `tests/test_lineage_service.py`
- Modify: `tests/test_inspect_view.py`
- Modify: `tests/test_sources_command.py`

- [ ] **Step 1: Write failing lineage snapshot tests for resolved targets, ambiguous targets, and cross-source reasoning**

```python
def test_lineage_service_returns_canonical_title_with_alternate_labels(tmp_path: Path) -> None:
    db = seeded_lineage_database(tmp_path)

    snapshot = LineageService().load_entity(db.path, target="eldenring.exe")

    assert snapshot.title == "ELDEN RING"
    assert snapshot.alternate_titles
    assert snapshot.confidence_reasons


def test_lineage_service_surfaces_source_conflicts(tmp_path: Path) -> None:
    db = seeded_conflict_database(tmp_path)

    snapshot = LineageService().load_sources(db.path, target="battle.net launcher")

    assert snapshot.conflicts
```

- [ ] **Step 2: Run the lineage tests and confirm the shared snapshot layer is missing**

Run: `uv run pytest tests/test_lineage_service.py tests/test_inspect_view.py tests/test_sources_command.py -q`
Expected: FAIL because `LineageService` and lineage snapshot models do not exist yet.

- [ ] **Step 3: Add the shared lineage dataclasses**

```python
@dataclass(slots=True)
class LineageContribution:
    source: str
    evidence_type: str
    strength: str
    reasoning: str


@dataclass(slots=True)
class EntityLineageSnapshot:
    title: str
    confidence: str
    confidence_reasons: list[str] = field(default_factory=list)
    alternate_titles: list[str] = field(default_factory=list)
    contributions: list[LineageContribution] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Re-run the lineage tests to confirm failures are behavioral**

Run: `uv run pytest tests/test_lineage_service.py tests/test_inspect_view.py tests/test_sources_command.py -q`
Expected: FAIL on missing behavior or assertions only.

- [ ] **Step 5: Commit the lineage-model scaffolding**

```bash
git add playtrace/models/lineage.py tests/test_lineage_service.py tests/test_inspect_view.py tests/test_sources_command.py
git commit -m "test: add lineage snapshot regressions"
```

## Task 7: Implement the Shared Lineage Service and Upgrade `inspect`

**Files:**
- Create: `playtrace/services/lineage.py`
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/services/inspector.py`
- Modify: `playtrace/render/source_views.py`
- Test: `tests/test_lineage_service.py`
- Test: `tests/test_inspect_view.py`

- [ ] **Step 1: Implement the shared entity-lineage loader**

```python
class LineageService:
    def load_entity(self, db_path: Path, target: str) -> EntityLineageSnapshot:
        ...
        return EntityLineageSnapshot(
            title=resolved_title,
            confidence=runtime_confidence,
            confidence_reasons=reasons,
            alternate_titles=alternate_titles,
            contributions=contributions,
            conflicts=conflicts,
        )
```

- [ ] **Step 2: Refactor `InspectorService` to delegate to the shared lineage layer**

```python
def load(self, request: InspectRequest) -> InspectionDetail:
    snapshot = self.lineage_service.load_entity(request.db_path, request.target)
    return InspectionDetail.from_lineage(snapshot)
```

- [ ] **Step 3: Upgrade the inspect renderer into a sectioned lineage dossier**

```python
console.print(Panel(..., title="Identity"))
console.print(Panel(..., title="Why This Won"))
console.print(Panel(..., title="Supporting Evidence"))
```

- [ ] **Step 4: Re-run the inspect and lineage tests**

Run: `uv run pytest tests/test_lineage_service.py tests/test_inspect_view.py -q`
Expected: PASS with resolved canonical title, alternate labels, evidence reasoning, and explicit ambiguous-target messaging.

- [ ] **Step 5: Commit the inspect upgrade**

```bash
git add playtrace/services/lineage.py playtrace/store/db.py playtrace/services/inspector.py playtrace/render/source_views.py tests/test_lineage_service.py tests/test_inspect_view.py
git commit -m "feat: add lineage-driven inspect view"
```

## Task 8: Implement Provenance-Rich `sources`

**Files:**
- Modify: `playtrace/services/sources.py`
- Modify: `playtrace/render/source_views.py`
- Test: `tests/test_lineage_service.py`
- Test: `tests/test_sources_command.py`

- [ ] **Step 1: Add failing provenance tests for per-source contributions, conflicts, and blocked-source context**

```python
def test_sources_view_groups_contributions_by_source_and_strength(tmp_path: Path) -> None:
    snapshot = SourcesService().load(...)

    assert snapshot.entries_by_source["security_log"][0].strength == "exact"
    assert snapshot.conflicts
```

- [ ] **Step 2: Run the sources tests and confirm the current service is still a flat raw row dump**

Run: `uv run pytest tests/test_sources_command.py tests/test_lineage_service.py -q`
Expected: FAIL because the current service only returns flat `SourceEntry` rows.

- [ ] **Step 3: Rebuild `SourcesService` on top of shared lineage snapshots**

```python
snapshot = self.lineage_service.load_sources(request.db_path, request.target)
render_sources(console, theme, snapshot)
```

- [ ] **Step 4: Upgrade the renderer into a grouped evidence ledger**

```python
table.add_column("Source")
table.add_column("Contribution")
table.add_column("Strength")
table.add_column("Observed")
table.add_column("Why It Matters")
```

- [ ] **Step 5: Re-run the sources tests**

Run: `uv run pytest tests/test_sources_command.py tests/test_lineage_service.py -q`
Expected: PASS with grouped contributions, explicit conflicts, and clearer provenance output.

- [ ] **Step 6: Commit the sources upgrade**

```bash
git add playtrace/services/sources.py playtrace/render/source_views.py tests/test_sources_command.py tests/test_lineage_service.py
git commit -m "feat: improve sources provenance view"
```

## Task 9: Add Export Lineage and Repair Diff Scopes with Config Integration

**Files:**
- Modify: `playtrace/services/exporter.py`
- Modify: `playtrace/cli/cmd_export.py`
- Modify: `playtrace/config/runtime.py`
- Modify: `playtrace/config/models.py`
- Modify: `playtrace/config/loader.py`
- Modify: `playtrace/config/resolver.py`
- Modify: `docs/config.example.toml`
- Modify: `tests/test_export_service.py`
- Modify: `tests/test_config_loader.py`
- Modify: `tests/test_config_resolver.py`
- Modify: `tests/test_command_config_integration.py`

- [ ] **Step 1: Write failing export tests for entity, lineage, and repair-diff scopes**

```python
def test_export_service_writes_lineage_scope_json(tmp_path: Path) -> None:
    ...
    ExporterService().run(ExportRequest(..., format="json", scope="lineage"))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "contributions" in payload["entity"]


def test_export_cli_scope_overrides_config_default(tmp_path: Path) -> None:
    ...
    result = runner.invoke(app, ["export", "--config", str(config_path), "--scope", "repair-preview", ...])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run the export and config tests and confirm the scope surface is not implemented**

Run: `uv run pytest tests/test_export_service.py tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py -q`
Expected: FAIL because `scope` is not part of export runtime/config yet.

- [ ] **Step 3: Implement export scope resolution and shared lineage/repair serialization**

```python
@dataclass(slots=True)
class RawExportInput:
    ...
    scope: str | object = UNSET


if resolved.scope == "lineage":
    payload = self._build_lineage_payload(...)
elif resolved.scope == "repair-preview":
    payload = self._build_repair_preview_payload(...)
```

- [ ] **Step 4: Re-run the export and config tests**

Run: `uv run pytest tests/test_export_service.py tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py -q`
Expected: PASS with config-backed default export scope and explicit CLI scope override.

- [ ] **Step 5: Commit the export and config integration**

```bash
git add playtrace/services/exporter.py playtrace/cli/cmd_export.py playtrace/config/runtime.py playtrace/config/models.py playtrace/config/loader.py playtrace/config/resolver.py docs/config.example.toml tests/test_export_service.py tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py
git commit -m "feat: add lineage and repair export scopes"
```

## Task 10: Run the Full Verification Matrix and Update the Validation Docs

**Files:**
- Modify: `docs/VALTEST.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: Run the focused automated suites**

Run: `uv run pytest tests/test_title_resolution.py tests/test_merge_sessions.py tests/test_rebuild_service.py tests/test_lineage_service.py tests/test_scan_service.py tests/test_doctor.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py tests/test_config_loader.py tests/test_config_resolver.py tests/test_command_config_integration.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Run hands-on CLI validation against a copied database**

Run:

```bash
uv run python -m playtrace scan --db <copy> --theme mono
uv run python -m playtrace scan --db <copy> --rebuild
uv run python -m playtrace scan --db <copy> --rebuild --yes
uv run python -m playtrace doctor --db <copy> --theme mono
uv run python -m playtrace doctor --db <copy> --repair
uv run python -m playtrace doctor --db <copy> --repair --yes
uv run python -m playtrace inspect --db <copy> "battle.net launcher" --theme mono
uv run python -m playtrace sources --db <copy> "battle.net launcher" --theme mono
uv run python -m playtrace export --db <copy> --format json --scope entity --output <entity.json>
uv run python -m playtrace export --db <copy> --format json --scope lineage --output <lineage.json>
uv run python -m playtrace export --db <copy> --format json --scope repair-preview --output <repair.json>
```

Expected: all commands exit `0`, rebuild preview shows counts without mutation until `--yes`, and lineage/export outputs reflect repaired truth or remaining ambiguity explicitly.

- [ ] **Step 4: Update the validation record and top-level TODO**

```markdown
- Added explicit repair validation for `scan --rebuild` and `doctor --repair`.
- Added lineage validation for `inspect`, `sources`, and export scopes.
```

- [ ] **Step 5: Commit the validation docs**

```bash
git add docs/VALTEST.md docs/TODO.md
git commit -m "docs: record reconstruction and lineage validation"
```
