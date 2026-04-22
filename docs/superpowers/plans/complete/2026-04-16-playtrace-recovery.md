# Playtrace Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover Playtrace into a truthful Windows CLI by rebuilding the evidence pipeline, reconstruction layer, audit layer, and rich command surfaces for `scan`, `me`, `report`, `titles`, `sessions`, `doctor`, `inspect`, `sources`, `map`, and `export`.

**Architecture:** Rebuild the system pipeline-first. First establish shared reconstructed and audited truth in the store/service layer. Then hang every command off typed snapshots and data-driven renderers so the CLI never depends on placeholders, silent execution, or bespoke ad hoc logic. Keep unknown, blocked, and weak-data states first-class throughout the pipeline and surface remediation guidance in every command.

**Tech Stack:** Python 3.13, Typer, Rich, SQLite, existing ingest/parsers/merge layers, pytest

---

## File Structure

### New Files

- `playtrace/models/doctor.py`
  - Dedicated doctor and remediation dataclasses so health findings stop being ad hoc dicts.
- `playtrace/models/dashboard.py`
  - Snapshot models for `playtrace me`, scan summaries, duplicate groups, and command-facing audit summaries.
- `playtrace/services/audit.py`
  - Shared environment and persisted-data audit engine used by `doctor`, `report`, and `me`.
- `playtrace/services/dashboard.py`
  - Snapshot builder for `playtrace me` and shared duplicate/remediation summaries.
- `playtrace/render/scan_views.py`
  - Rich sections for live scan progress, per-source status, and final scan summary.
- `playtrace/render/dashboard_views.py`
  - Neofetch-style renderer for `playtrace me`.
- `playtrace/render/doctor_views.py`
  - Doctor audit rendering with severity grouping and remediation panels.
- `tests/test_scan_service.py`
  - Behavioral tests for live scan summary generation and progress-oriented service behavior.
- `tests/test_audit_service.py`
  - Tests for environment and persisted-data audit findings.
- `tests/test_dashboard_service.py`
  - Tests for `me` snapshot building and refresh semantics.
- `tests/test_export_service.py`
  - Tests for recovered export behavior.

### Modified Files

- `playtrace/cli/app.py`
  - Register the new `me` command and updated breaking CLI surfaces.
- `playtrace/cli/cmd_scan.py`
  - Expand scan flags and wire into the recovered live-scan service.
- `playtrace/cli/cmd_report.py`
  - Add deeper report flags without bloating default output.
- `playtrace/cli/cmd_titles.py`
  - Update flags and help text to match the recovered title surface.
- `playtrace/cli/cmd_sessions.py`
  - Update flags and help text to match the recovered session surface.
- `playtrace/cli/cmd_doctor.py`
  - Add audit-oriented options and breaking-surface changes.
- `playtrace/cli/cmd_inspect.py`
  - Rewire to shared truth layer and surfaced remediation context.
- `playtrace/cli/cmd_sources.py`
  - Rewire to shared truth layer and richer evidence output.
- `playtrace/cli/cmd_map.py`
  - Support reintegrated mapping flow and duplicate remediation semantics.
- `playtrace/cli/cmd_export.py`
  - Wire export to actual snapshot/query builders instead of stubs.
- `playtrace/services/scanner.py`
  - Emit live scan state, persist scan-run summaries, and render final results.
- `playtrace/services/reporter.py`
  - Replace placeholders and stubs with shared snapshot builders and flag-driven sections.
- `playtrace/services/doctor.py`
  - Delegate to the audit engine and render real findings instead of readiness-only status.
- `playtrace/services/inspector.py`
  - Align detail loading with shared reconstructed and audited truth.
- `playtrace/services/sources.py`
  - Align source lookups and degraded-state handling with recovered evidence graph semantics.
- `playtrace/services/mapper.py`
  - Rebuild mappings through reconstruction refresh and duplicate-aware outputs.
- `playtrace/services/exporter.py`
  - Replace `NotImplementedError` with snapshot-driven export logic.
- `playtrace/ingest/orchestrator.py`
  - Add structured progress events and collector/parser status summaries.
- `playtrace/merge/sessions.py`
  - Improve partial/open session truth handling and confidence assignment.
- `playtrace/merge/titles.py`
  - Improve title grouping, duplicate candidate generation, and unknown-state handling.
- `playtrace/classify/resolver.py`
  - Tighten title resolution heuristics and duplicate grouping inputs.
- `playtrace/models/report.py`
  - Expand report snapshot beyond current placeholder-heavy coverage structure.
- `playtrace/store/db.py`
  - Add query helpers, persisted audit support, duplicate candidate storage/queries, and truthful snapshot loaders.
- `playtrace/render/report_views.py`
  - Render recovered snapshot sections and optional deep report panels.
- `playtrace/render/source_views.py`
  - Render inspect and source details with remediation and degraded-state context.
- `playtrace/render/tables.py`
  - Add tables for duplicate groups, richer sessions, and confidence-aware rows.
- `tests/test_report_render.py`
  - Expand snapshot and rendering coverage around recovered report/titles/sessions behavior.
- `tests/test_doctor.py`
  - Replace readiness-only assertions with environment and data-audit expectations.
- `tests/test_sources_command.py`
  - Update source view expectations to the shared truth layer.
- `tests/test_inspect_view.py`
  - Update inspection expectations to include confidence and remediation context.
- `tests/test_mapping_service.py`
  - Cover reintegrated mapping and refresh semantics.
- `tests/test_title_resolution.py`
  - Cover duplicate candidate detection and auto-merge heuristics.
- `docs/TODO.md`
  - Record recovery work items and close them as implementation lands.

### Existing Files to Read During Implementation

- `docs/superpowers/specs/2026-04-16-playtrace-recovery-design.md`
- `playtrace/ingest/registry.py`
- `playtrace/parsers/base.py`
- `playtrace/models/title.py`
- `playtrace/models/session.py`
- `playtrace/render/theme.py`

## Task 1: Establish Shared Recovery Models and Database Query Surface

**Files:**
- Create: `playtrace/models/doctor.py`
- Create: `playtrace/models/dashboard.py`
- Modify: `playtrace/models/report.py`
- Modify: `playtrace/store/db.py`
- Test: `tests/test_report_render.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing tests for the expanded snapshot/query contract**

```python
def test_load_snapshot_includes_recent_sessions_and_unmapped_count(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    # seed titles + sessions + unmapped evidence here
    snapshot = db.load_snapshot(limit=5)
    assert snapshot.coverage.unmapped_executables == 1
    assert snapshot.recent_sessions


def test_doctor_snapshot_can_hold_environment_and_data_findings() -> None:
    snapshot = DoctorSnapshot(environment_findings=[], data_findings=[])
    assert snapshot.environment_findings == []
    assert snapshot.data_findings == []
```

- [ ] **Step 2: Run the targeted tests to verify the contract fails for the expected reason**

Run: `uv run pytest tests/test_report_render.py tests/test_doctor.py -q`
Expected: FAIL because the current report snapshot model/query surface does not provide recent sessions, unmapped counts, or dedicated doctor findings models.

- [ ] **Step 3: Implement the minimal shared models and database loaders**

```python
@dataclass(slots=True)
class DoctorFinding:
    severity: str
    code: str
    summary: str
    remediation: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IdentityDashboardSnapshot:
    generated_at: datetime
    host_name: str
    scan_age: str
    top_titles: list[TitleAggregate] = field(default_factory=list)
```

- [ ] **Step 4: Re-run the targeted tests until the new snapshot/query surface passes**

Run: `uv run pytest tests/test_report_render.py tests/test_doctor.py -q`
Expected: PASS with new snapshot fields and database loaders available.

- [ ] **Step 5: Commit the snapshot-layer groundwork**

```bash
git add playtrace/models/doctor.py playtrace/models/dashboard.py playtrace/models/report.py playtrace/store/db.py tests/test_report_render.py tests/test_doctor.py
git commit -m "Build shared recovery snapshots and db loaders"
```

## Task 2: Instrument the Scan Pipeline for Live Progress and Truthful Final Summaries

**Files:**
- Modify: `playtrace/ingest/orchestrator.py`
- Modify: `playtrace/services/scanner.py`
- Create: `playtrace/render/scan_views.py`
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/cli/cmd_scan.py`
- Test: `tests/test_scan_service.py`

- [ ] **Step 1: Write the failing tests for live scan summaries and non-silent output**

```python
def test_scan_service_returns_source_statuses_and_final_summary(tmp_path: Path) -> None:
    request = ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False)
    snapshot = ScannerService().run_for_snapshot(request)
    assert snapshot.sources
    assert snapshot.summary.total_artifacts >= 0


def test_scan_command_never_finishes_without_rendering_summary(tmp_path: Path, capsys) -> None:
    ScannerService().render(ScanRequest(db_path=tmp_path / "playtrace.db", config_path=None, sources=[], full=False))
    assert "playtrace SCAN" in capsys.readouterr().out
```

- [ ] **Step 2: Run the scan-focused tests and confirm they fail because no live snapshot/render path exists**

Run: `uv run pytest tests/test_scan_service.py -q`
Expected: FAIL because the current scanner only ingests and exits.

- [ ] **Step 3: Implement progress events, persisted scan summaries, and live rendering**

```python
@dataclass(slots=True)
class ScanSourceStatus:
    source: str
    status: str
    artifacts: int = 0
    evidence: int = 0
    warnings: list[str] = field(default_factory=list)


class ScannerService:
    def run_for_snapshot(self, request: ScanRequest) -> ScanLiveSnapshot:
        ...
```

- [ ] **Step 4: Re-run the scan tests and the CLI smoke test**

Run: `uv run pytest tests/test_scan_service.py -q`
Expected: PASS with a rendered scan banner and final summary.

- [ ] **Step 5: Commit the live scan recovery**

```bash
git add playtrace/ingest/orchestrator.py playtrace/services/scanner.py playtrace/render/scan_views.py playtrace/store/db.py playtrace/cli/cmd_scan.py tests/test_scan_service.py
git commit -m "Recover live scan pipeline and rendering"
```

## Task 3: Build the Audit Engine and Rework `doctor`

**Files:**
- Create: `playtrace/services/audit.py`
- Modify: `playtrace/services/doctor.py`
- Create: `playtrace/render/doctor_views.py`
- Modify: `playtrace/cli/cmd_doctor.py`
- Modify: `playtrace/store/db.py`
- Test: `tests/test_audit_service.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing tests for environment and persisted-data audits**

```python
def test_audit_engine_reports_blocked_sources_and_duplicate_titles(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    snapshot = AuditService().load(AuditRequest(db_path=db.path))
    assert snapshot.environment_findings is not None
    assert snapshot.data_findings is not None


def test_doctor_render_includes_remediation_guidance(tmp_path: Path, capsys) -> None:
    DoctorService().render(DoctorRequest(db_path=tmp_path / "playtrace.db", theme="mono"))
    assert "How to correct this" in capsys.readouterr().out
```

- [ ] **Step 2: Run the doctor/audit tests to verify the current readiness-only implementation fails**

Run: `uv run pytest tests/test_audit_service.py tests/test_doctor.py -q`
Expected: FAIL because there is no shared audit engine or remediation section.

- [ ] **Step 3: Implement the audit engine and doctor rendering**

```python
class AuditService:
    def load(self, request: AuditRequest) -> DoctorSnapshot:
        return DoctorSnapshot(
            environment_findings=self._environment_findings(request),
            data_findings=self._data_findings(request),
        )
```

- [ ] **Step 4: Re-run the doctor/audit tests**

Run: `uv run pytest tests/test_audit_service.py tests/test_doctor.py -q`
Expected: PASS with both environment and persisted-data findings.

- [ ] **Step 5: Commit the recovered doctor path**

```bash
git add playtrace/services/audit.py playtrace/services/doctor.py playtrace/render/doctor_views.py playtrace/cli/cmd_doctor.py playtrace/store/db.py tests/test_audit_service.py tests/test_doctor.py
git commit -m "Turn doctor into environment and data audit"
```

## Task 4: Rebuild Report, Titles, and Sessions on Shared Snapshots

**Files:**
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/render/report_views.py`
- Modify: `playtrace/render/tables.py`
- Modify: `playtrace/cli/cmd_report.py`
- Modify: `playtrace/cli/cmd_titles.py`
- Modify: `playtrace/cli/cmd_sessions.py`
- Modify: `playtrace/store/db.py`
- Test: `tests/test_report_render.py`

- [ ] **Step 1: Extend the report/titles/sessions tests to cover real snapshot behavior**

```python
def test_render_report_defaults_to_light_snapshot_without_placeholders(tmp_path: Path, capsys) -> None:
    ReporterService().render_default(ReportRequest(...))
    output = capsys.readouterr().out
    assert "Recent Sessions" in output
    assert "0h 00m" not in output or "UNKNOWN" in output


def test_render_report_duplicates_flag_surfaces_candidate_groups(tmp_path: Path, capsys) -> None:
    ReporterService().render_default(ReportRequest(..., show_duplicates=True))
    assert "Duplicate Candidates" in capsys.readouterr().out
```

- [ ] **Step 2: Run report/titles/sessions tests and confirm the current service layer fails on missing logic or placeholder fields**

Run: `uv run pytest tests/test_report_render.py -q`
Expected: FAIL because the current report snapshot is incomplete and titles/sessions are stubbed or underpowered on `main`.

- [ ] **Step 3: Implement shared snapshot builders and flag-driven sections**

```python
class ReporterService:
    def build_report_snapshot(self, request: ReportRequest) -> ReportSnapshot:
        ...

    def render_titles(self, request: TitlesRequest) -> None:
        ...

    def render_sessions(self, request: SessionsRequest) -> None:
        ...
```

- [ ] **Step 4: Re-run the report/titles/sessions tests**

Run: `uv run pytest tests/test_report_render.py -q`
Expected: PASS with truthful recent sessions, unmapped counts, unknown-state handling, and deep report flags.

- [ ] **Step 5: Commit the reporter recovery**

```bash
git add playtrace/services/reporter.py playtrace/render/report_views.py playtrace/render/tables.py playtrace/cli/cmd_report.py playtrace/cli/cmd_titles.py playtrace/cli/cmd_sessions.py playtrace/store/db.py tests/test_report_render.py
git commit -m "Recover report titles and sessions snapshots"
```

## Task 5: Add `playtrace me` and the Identity Dashboard Snapshot

**Files:**
- Create: `playtrace/services/dashboard.py`
- Create: `playtrace/render/dashboard_views.py`
- Modify: `playtrace/cli/app.py`
- Create: `playtrace/cli/cmd_me.py`
- Create: `tests/test_dashboard_service.py`

- [ ] **Step 1: Write the failing tests for the dashboard snapshot and `--refresh` semantics**

```python
def test_dashboard_service_loads_latest_persisted_identity_snapshot(tmp_path: Path) -> None:
    snapshot = DashboardService().load(DashboardRequest(db_path=tmp_path / "playtrace.db", refresh=False))
    assert snapshot.top_titles is not None


def test_dashboard_refresh_runs_scan_before_render(tmp_path: Path) -> None:
    service = DashboardService(scanner=FakeScannerService())
    service.render(DashboardRequest(db_path=tmp_path / "playtrace.db", refresh=True, theme="mono"))
    assert service.scanner.called
```

- [ ] **Step 2: Run the dashboard tests to verify the command and service do not exist yet**

Run: `uv run pytest tests/test_dashboard_service.py -q`
Expected: FAIL because there is no `me` command or dashboard service.

- [ ] **Step 3: Implement the dashboard service, renderer, and CLI registration**

```python
@app.command("me")
def me(...) -> None:
    DashboardService().render(DashboardRequest(...))
```

- [ ] **Step 4: Re-run the dashboard tests**

Run: `uv run pytest tests/test_dashboard_service.py -q`
Expected: PASS with default stored-data loading and `--refresh` scanning.

- [ ] **Step 5: Commit the `me` command**

```bash
git add playtrace/services/dashboard.py playtrace/render/dashboard_views.py playtrace/cli/app.py playtrace/cli/cmd_me.py tests/test_dashboard_service.py
git commit -m "Add playtrace me identity dashboard"
```

## Task 6: Surface Duplicates and Implement Aggressive `--auto` Merging

**Files:**
- Modify: `playtrace/classify/resolver.py`
- Modify: `playtrace/merge/titles.py`
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/services/mapper.py`
- Modify: `playtrace/cli/cmd_map.py`
- Test: `tests/test_title_resolution.py`
- Test: `tests/test_mapping_service.py`

- [ ] **Step 1: Write the failing tests for duplicate candidate detection and `--auto` remediation**

```python
def test_title_resolution_emits_duplicate_candidates_for_similar_executables() -> None:
    result = TitleResolver().resolve(executables, sessions, mappings=[])
    assert result.duplicate_candidates


def test_mapper_auto_merge_rebuilds_titles_after_applying_heuristics(tmp_path: Path) -> None:
    MapperService().apply_auto_merge(MapRequest(..., auto=True))
    rebuilt = Database(tmp_path / "playtrace.db").load_snapshot(limit=10)
    assert rebuilt.coverage.tracked_titles == 1
```

- [ ] **Step 2: Run the duplicate/mapping tests and confirm the current pipeline does not support this behavior**

Run: `uv run pytest tests/test_title_resolution.py tests/test_mapping_service.py -q`
Expected: FAIL because duplicate candidates and auto-merge semantics do not exist.

- [ ] **Step 3: Implement duplicate candidate generation and `--auto` merge flow**

```python
class DuplicateCandidate:
    primary_title_id: str
    related_title_ids: list[str]
    reasons: list[str]


class MapperService:
    def apply_auto_merge(self, request: MapRequest) -> None:
        ...
```

- [ ] **Step 4: Re-run the duplicate/mapping tests**

Run: `uv run pytest tests/test_title_resolution.py tests/test_mapping_service.py -q`
Expected: PASS with surfaced duplicate groups and aggressive merge support.

- [ ] **Step 5: Commit duplicate remediation**

```bash
git add playtrace/classify/resolver.py playtrace/merge/titles.py playtrace/store/db.py playtrace/services/reporter.py playtrace/services/mapper.py playtrace/cli/cmd_map.py tests/test_title_resolution.py tests/test_mapping_service.py
git commit -m "Add duplicate detection and auto merge"
```

## Task 7: Reintegrate Inspect, Sources, and Export with the Shared Truth Layer

**Files:**
- Modify: `playtrace/services/inspector.py`
- Modify: `playtrace/services/sources.py`
- Modify: `playtrace/services/exporter.py`
- Modify: `playtrace/render/source_views.py`
- Modify: `playtrace/cli/cmd_export.py`
- Modify: `playtrace/cli/cmd_inspect.py`
- Modify: `playtrace/cli/cmd_sources.py`
- Create: `tests/test_export_service.py`
- Modify: `tests/test_inspect_view.py`
- Modify: `tests/test_sources_command.py`

- [ ] **Step 1: Write the failing tests for aligned inspect/source/export behavior**

```python
def test_export_service_writes_snapshot_driven_json(tmp_path: Path) -> None:
    request = ExportRequest(db_path=tmp_path / "playtrace.db", output_path=tmp_path / "out.json", format="json")
    ExporterService().run(request)
    assert request.output_path.exists()


def test_inspect_render_includes_remediation_context(tmp_path: Path, capsys) -> None:
    InspectorService().render(InspectRequest(...))
    assert "Confidence reasoning" in capsys.readouterr().out
```

- [ ] **Step 2: Run the inspect/source/export tests to confirm the current surface is incomplete**

Run: `uv run pytest tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py -q`
Expected: FAIL because export is still stubbed and inspect/sources are not fully aligned with the recovered truth layer.

- [ ] **Step 3: Implement snapshot-driven export and reintegrated inspect/source services**

```python
class ExporterService:
    def run(self, request: ExportRequest) -> None:
        payload = self._build_export_payload(request)
        request.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Re-run the inspect/source/export tests**

Run: `uv run pytest tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py -q`
Expected: PASS with richer evidence context and working export behavior.

- [ ] **Step 5: Commit secondary command reintegration**

```bash
git add playtrace/services/inspector.py playtrace/services/sources.py playtrace/services/exporter.py playtrace/render/source_views.py playtrace/cli/cmd_export.py playtrace/cli/cmd_inspect.py playtrace/cli/cmd_sources.py tests/test_inspect_view.py tests/test_sources_command.py tests/test_export_service.py
git commit -m "Reintegrate inspect sources and export"
```

## Task 8: Raise the Visual Quality Bar Across the Recovered CLI

**Files:**
- Modify: `playtrace/render/theme.py`
- Modify: `playtrace/render/cards.py`
- Modify: `playtrace/render/report_views.py`
- Modify: `playtrace/render/scan_views.py`
- Modify: `playtrace/render/dashboard_views.py`
- Modify: `playtrace/render/doctor_views.py`
- Modify: `playtrace/render/source_views.py`
- Test: `tests/test_report_render.py`
- Test: `tests/test_scan_service.py`
- Test: `tests/test_dashboard_service.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write or extend render tests for the final visual contract**

```python
def test_dashboard_render_uses_identity_block_sections(tmp_path: Path, capsys) -> None:
    DashboardService().render(DashboardRequest(...))
    output = capsys.readouterr().out
    assert "playtrace ME" in output
    assert "Coverage" in output


def test_scan_render_shows_source_status_table_and_final_metrics(tmp_path: Path, capsys) -> None:
    ScannerService().render(...)
    output = capsys.readouterr().out
    assert "Source" in output
    assert "Summary" in output
```

- [ ] **Step 2: Run the rendering tests and note the visual gaps**

Run: `uv run pytest tests/test_report_render.py tests/test_scan_service.py tests/test_dashboard_service.py tests/test_doctor.py -q`
Expected: FAIL on the newly asserted presentation sections until the render layer is updated.

- [ ] **Step 3: Implement the final render refinements without changing command truth**

```python
def render_remediation_panel(...) -> Panel:
    ...


def render_identity_block(...) -> RenderableType:
    ...
```

- [ ] **Step 4: Re-run the rendering tests**

Run: `uv run pytest tests/test_report_render.py tests/test_scan_service.py tests/test_dashboard_service.py tests/test_doctor.py -q`
Expected: PASS with the final visual contract represented in output.

- [ ] **Step 5: Commit the CLI presentation polish**

```bash
git add playtrace/render/theme.py playtrace/render/cards.py playtrace/render/report_views.py playtrace/render/scan_views.py playtrace/render/dashboard_views.py playtrace/render/doctor_views.py playtrace/render/source_views.py tests/test_report_render.py tests/test_scan_service.py tests/test_dashboard_service.py tests/test_doctor.py
git commit -m "Polish recovered cli rendering"
```

## Task 9: Update Docs, Run Full Verification, and Prepare Integration

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/CHANGELOG.md`
- Verify: full test suite via `uv run pytest -q`

- [ ] **Step 1: Add or update TODO and changelog entries describing the recovery work**

```markdown
- [x] Recover scan, me, report, titles, sessions, doctor, inspect, sources, map, and export on shared truth-layer snapshots.
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS with the recovered command, pipeline, audit, and render coverage.

- [ ] **Step 3: Run CLI smoke checks against a real database**

Run: `uv run python -m playtrace scan --db playtrace.db`
Expected: renders live scan UI and final summary

Run: `uv run python -m playtrace me --db playtrace.db`
Expected: renders the neofetch-style identity dashboard from stored data

Run: `uv run python -m playtrace report --db playtrace.db`
Expected: renders a truthful light snapshot with no placeholder sections

Run: `uv run python -m playtrace doctor --db playtrace.db`
Expected: renders environment and data audit findings with remediation guidance

- [ ] **Step 4: Verify the worktree is clean**

Run: `git status --short`
Expected: no output

- [ ] **Step 5: Commit docs and final cleanup**

```bash
git add docs/TODO.md docs/CHANGELOG.md
git commit -m "Document Playtrace recovery rollout"
```

## Local Review Notes

The writing-plans skill normally calls for a separate plan-document-reviewer subagent. In this session, no explicit delegation permission was granted, so do a local review before execution:

- Re-read `docs/superpowers/specs/2026-04-16-playtrace-recovery-design.md`
- Verify every command named in the spec appears in this plan
- Verify each task starts with a failing test, includes the command to prove failure, and ends with a commit step
- Verify the plan remains pipeline-first instead of front-loading presentation changes
- Verify all new files and modified files have exact paths

If any of those checks fail, revise this plan before execution starts.
