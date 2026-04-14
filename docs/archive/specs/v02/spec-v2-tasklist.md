# SPEC v2 Implementation Plan

> **Audit status (2026-04-14):** Reviewed against the current source tree and verified with `uv run pytest`, `uv run python -m playtrace --help`, `uv run python -m playtrace sources --help`, and `uv run python -m playtrace doctor --help`. Historical TDD and commit checkpoints are marked complete because the corresponding tests, implementation, and landed history are present in the repo.

**Goal:** Replace the current scaffold-first pipeline with an evidence-first Playtrace v2 that stores raw provenance, derives exact and inferred evidence separately, resolves titles through executable relationships, and exposes that provenance through the CLI.

**Architecture:** Keep the current Python package layout and Typer CLI surface, but split the data path into raw collection, evidence parsing, normalization, session merge, title resolution, and reporting. SQLite remains the source of truth, but aggregates must be rebuildable from persisted raw artifacts and user mappings instead of being treated as primary data.

**Tech Stack:** Python 3.12+, Typer, Rich, sqlite3, pytest

---

## File Map

### Core model and storage changes

- Create: `playtrace/models/evidence.py`
- Create: `playtrace/models/scan_run.py`
- Modify: `playtrace/models/enums.py`
- Modify: `playtrace/store/schema.py`
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/store/repositories.py`

### Ingest and parser pipeline

- Create: `playtrace/ingest/security_log.py`
- Create: `playtrace/ingest/prefetch.py`
- Create: `playtrace/ingest/userassist.py`
- Create: `playtrace/ingest/amcache.py`
- Create: `playtrace/ingest/srum.py`
- Create: `playtrace/ingest/bam.py`
- Modify: `playtrace/ingest/orchestrator.py`
- Modify: `playtrace/ingest/registry.py`
- Modify: `playtrace/parsers/base.py`
- Modify: `playtrace/parsers/security_log.py`
- Modify: `playtrace/parsers/prefetch.py`
- Modify: `playtrace/parsers/userassist.py`
- Modify: `playtrace/parsers/amcache.py`
- Modify: `playtrace/parsers/srum.py`
- Modify: `playtrace/parsers/bam.py`

### Merge, classify, and resolve

- Modify: `playtrace/normalize/identity.py`
- Modify: `playtrace/merge/sessions.py`
- Modify: `playtrace/merge/titles.py`
- Modify: `playtrace/merge/confidence.py`
- Modify: `playtrace/classify/rules.py`
- Modify: `playtrace/classify/heuristics.py`
- Modify: `playtrace/classify/resolver.py`
- Modify: `playtrace/models/executable.py`
- Modify: `playtrace/models/session.py`
- Modify: `playtrace/models/title.py`
- Modify: `playtrace/models/mapping.py`

### CLI, rendering, and provenance inspection

- Create: `playtrace/cli/cmd_sources.py`
- Create: `playtrace/services/sources.py`
- Create: `playtrace/render/source_views.py`
- Modify: `playtrace/cli/app.py`
- Modify: `playtrace/cli/common.py`
- Modify: `playtrace/services/scanner.py`
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/services/inspector.py`
- Modify: `playtrace/services/mapper.py`
- Modify: `playtrace/services/doctor.py`
- Modify: `playtrace/render/report_views.py`
- Modify: `playtrace/render/tables.py`
- Modify: `playtrace/render/cards.py`
- Modify: `playtrace/render/timeline.py`

### Tests and fixtures

- Create: `tests/test_store_schema.py`
- Create: `tests/test_security_log_pipeline.py`
- Create: `tests/test_sources_command.py`
- Create: `tests/test_inspect_view.py`
- Create: `tests/test_title_resolution.py`
- Create: `tests/test_doctor.py`
- Modify: `tests/test_identity.py`
- Modify: `tests/test_merge_sessions.py`
- Modify: `tests/test_classification.py`
- Modify: `tests/test_report_render.py`
- Create: `tests/fixtures/security_log/events.json`
- Create: `tests/fixtures/prefetch/sample.json`
- Create: `tests/fixtures/userassist/sample.json`
- Create: `tests/fixtures/amcache/sample.json`
- Create: `tests/fixtures/srum/sample.csv`
- Create: `tests/fixtures/bam/sample.json`

---

### Task 1: Add Provenance Models and V2 Storage Tables

**Files:**
- Create: `playtrace/models/evidence.py`
- Create: `playtrace/models/scan_run.py`
- Modify: `playtrace/models/enums.py`
- Modify: `playtrace/store/schema.py`
- Modify: `playtrace/store/db.py`
- Test: `tests/test_store_schema.py`

- [x] **Step 1: Write the failing schema bootstrap test**

```python
def test_bootstrap_creates_v2_tables(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()

    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"scan_runs", "artifacts", "evidence_links", "title_executables"} <= names
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store_schema.py::test_bootstrap_creates_v2_tables -v`
Expected: FAIL because the v2 provenance tables do not exist yet.

- [x] **Step 3: Add explicit evidence and scan-run models**

```python
@dataclass(slots=True)
class RawArtifact:
    artifact_id: str
    scan_run_id: str
    source: SourceName
    observed_at: datetime | None
    payload: dict[str, Any]
    raw_ref: str


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    artifact_id: str
    source: SourceName
    evidence_type: EvidenceType
    observed_at: datetime | None
    value: dict[str, Any]
    strength: EvidenceStrength
```

- [x] **Step 4: Extend enums for evidence typing and confidence separation**

```python
class EvidenceType(str, Enum):
    PROCESS_START = "process_start"
    PROCESS_EXIT = "process_exit"
    EXECUTION_COUNT = "execution_count"
    INTERACTIVE_LAUNCH = "interactive_launch"
    ACTIVITY_WINDOW = "activity_window"
    IDENTITY = "identity"
```

- [x] **Step 5: Replace the current schema with a provenance-first schema**

Add `scan_runs`, `artifacts`, `evidence_links`, and `title_executables`, while keeping `executables`, `sessions`, `titles`, and `mappings`.

```sql
CREATE TABLE IF NOT EXISTS scan_runs (
    scan_run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    host_name TEXT NOT NULL,
    selected_sources TEXT NOT NULL,
    warnings TEXT NOT NULL
);
```

- [x] **Step 6: Add database methods for scan tracking and raw persistence**

Implement methods such as:

```python
def create_scan_run(self, selected_sources: list[str]) -> str: ...
def finish_scan_run(self, scan_run_id: str, warnings: list[str]) -> None: ...
def replace_artifacts_for_scan(self, scan_run_id: str, artifacts: list[RawArtifact]) -> None: ...
def replace_evidence_for_scan(self, scan_run_id: str, records: list[EvidenceRecord]) -> None: ...
```

- [x] **Step 7: Run the schema test**

Run: `uv run pytest tests/test_store_schema.py -v`
Expected: PASS.

- [x] **Step 8: Commit**

```bash
git add playtrace/models/evidence.py playtrace/models/scan_run.py playtrace/models/enums.py playtrace/store/schema.py playtrace/store/db.py tests/test_store_schema.py
git commit -m "feat: add provenance-first v2 storage"
```

### Task 2: Introduce the Raw Collection -> Evidence Parsing Pipeline

**Files:**
- Modify: `playtrace/parsers/base.py`
- Modify: `playtrace/ingest/orchestrator.py`
- Modify: `playtrace/ingest/registry.py`
- Create: `playtrace/ingest/security_log.py`
- Modify: `playtrace/services/scanner.py`
- Test: `tests/test_security_log_pipeline.py`

- [x] **Step 1: Write the failing pipeline test**

```python
def test_scan_pipeline_stores_raw_artifacts_before_sessions(tmp_path: Path) -> None:
    db = Database(tmp_path / "playtrace.db")
    db.bootstrap()
    service = ScannerService()

    request = ScanRequest(db_path=db.path, config_path=None, sources=["security_log"], full=True)
    service.run(request)

    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] >= 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_security_log_pipeline.py::test_scan_pipeline_stores_raw_artifacts_before_sessions -v`
Expected: FAIL because `ScannerService.run()` is still unimplemented.

- [x] **Step 3: Split collector and parser contracts**

Replace the single parser-only contract with separate protocols:

```python
class RawCollector(Protocol):
    name: str
    def is_available(self) -> bool: ...
    def collect(self, context: CollectContext) -> list[RawArtifact]: ...


class EvidenceParser(Protocol):
    name: str
    def parse(self, artifacts: Sequence[RawArtifact]) -> list[EvidenceRecord]: ...
```

- [x] **Step 4: Add a Security Log collector in `playtrace/ingest/security_log.py`**

Start with fixture-driven collection so the pipeline works before native Windows integration. Return `RawArtifact` payloads shaped like:

```python
{
    "event_id": 4688,
    "timestamp": "2026-04-11T18:42:03Z",
    "pid": 15320,
    "parent_pid": 9012,
    "exe_path": "D:\\SteamLibrary\\...\\eldenring.exe",
}
```

- [x] **Step 5: Update the orchestrator to collect raw artifacts, parse evidence, and persist both**

`IngestResult` should carry both `artifacts` and `evidence`.

```python
@dataclass(slots=True)
class IngestResult:
    artifacts: list[RawArtifact]
    evidence: list[EvidenceRecord]
    warnings: list[str]
```

- [x] **Step 6: Implement `ScannerService.run()` as the top-level persistence coordinator**

Responsibilities:
- create scan run
- invoke orchestrator
- persist artifacts
- persist evidence
- call downstream normalization and merge code only after evidence is stored
- finish the scan run with warnings

- [x] **Step 7: Run the pipeline test**

Run: `uv run pytest tests/test_security_log_pipeline.py -v`
Expected: PASS for raw artifact persistence.

- [x] **Step 8: Commit**

```bash
git add playtrace/parsers/base.py playtrace/ingest/orchestrator.py playtrace/ingest/registry.py playtrace/ingest/security_log.py playtrace/services/scanner.py tests/test_security_log_pipeline.py
git commit -m "feat: split raw collection from evidence parsing"
```

### Task 3: Implement Exact Security Session Pairing and Executable Normalization

**Files:**
- Modify: `playtrace/parsers/security_log.py`
- Modify: `playtrace/normalize/identity.py`
- Modify: `playtrace/merge/sessions.py`
- Modify: `playtrace/models/executable.py`
- Modify: `playtrace/models/session.py`
- Modify: `tests/test_identity.py`
- Modify: `tests/test_merge_sessions.py`
- Create: `tests/fixtures/security_log/events.json`

- [x] **Step 1: Write failing normalization and session-pairing tests**

```python
def test_identity_normalizer_merges_case_only_path_variants() -> None: ...
def test_session_merger_pairs_4688_and_4689_by_pid() -> None: ...
```

- [x] **Step 2: Run those tests to verify they fail**

Run: `uv run pytest tests/test_identity.py tests/test_merge_sessions.py -v`
Expected: FAIL because the current normalizer and merger are stub-level.

- [x] **Step 3: Upgrade the security parser to emit semantic evidence**

Map raw 4688 events to `process_start` evidence and 4689 events to `process_exit` evidence. Preserve PID, parent PID, executable path, command line, and SID.

- [x] **Step 4: Replace the soft hash-only identity builder with path-aware normalization**

Support:
- lowercase and slash normalization
- quoted command-line trimming
- executable path extraction
- hash-first identity
- fallback to `original_filename + product_name + signer`

```python
def build_key(self, evidence: EvidenceRecord) -> str:
    if sha1:
        return f"sha1:{sha1}"
    if canonical_path:
        return f"path:{canonical_path}"
    return f"soft:{digest}"
```

- [x] **Step 5: Implement exact session pairing in `playtrace/merge/sessions.py`**

Pair `process_start` and `process_exit` records by `(pid, normalized_exe, user_sid)` and emit exact sessions when both exist. Emit partial sessions when only a start exists.

- [x] **Step 6: Preserve provenance on each session**

Ensure each `SessionRecord` stores:
- exact or estimated runtime confidence
- evidence source list
- parent chain
- raw artifact or evidence IDs needed for inspection

- [x] **Step 7: Run the identity and merge tests**

Run: `uv run pytest tests/test_identity.py tests/test_merge_sessions.py -v`
Expected: PASS.

- [x] **Step 8: Commit**

```bash
git add playtrace/parsers/security_log.py playtrace/normalize/identity.py playtrace/merge/sessions.py playtrace/models/executable.py playtrace/models/session.py tests/test_identity.py tests/test_merge_sessions.py tests/fixtures/security_log/events.json
git commit -m "feat: add exact session pairing and executable normalization"
```

### Task 4: Add Prefetch, UserAssist, and AmCache as Supporting Evidence Sources

**Files:**
- Create: `playtrace/ingest/prefetch.py`
- Create: `playtrace/ingest/userassist.py`
- Create: `playtrace/ingest/amcache.py`
- Modify: `playtrace/parsers/prefetch.py`
- Modify: `playtrace/parsers/userassist.py`
- Modify: `playtrace/parsers/amcache.py`
- Create: `tests/fixtures/prefetch/sample.json`
- Create: `tests/fixtures/userassist/sample.json`
- Create: `tests/fixtures/amcache/sample.json`
- Modify: `tests/test_classification.py`

- [x] **Step 1: Write fixture-driven parser tests for Prefetch, UserAssist, and AmCache**

```python
def test_prefetch_parser_emits_execution_count_evidence() -> None: ...
def test_userassist_parser_emits_interactive_launch_and_focus() -> None: ...
def test_amcache_parser_emits_identity_evidence() -> None: ...
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_classification.py -v`
Expected: FAIL until the supporting-source parsers emit evidence records.

- [x] **Step 3: Implement raw collectors for these sources**

Each collector should load source-native fixture payloads first, then allow native Windows collection later without changing downstream parser contracts.

- [x] **Step 4: Parse these sources into explicit evidence types**

Examples:

```python
EvidenceType.EXECUTION_COUNT
EvidenceType.INTERACTIVE_LAUNCH
EvidenceType.FOREGROUND_USAGE
EvidenceType.IDENTITY
```

- [x] **Step 5: Assign source strength without faking runtime precision**

Use:
- Prefetch -> `STRONG`
- UserAssist -> `INTERACTIVE`
- AmCache -> `STRONG` for identity only

- [x] **Step 6: Run the parser tests**

Run: `uv run pytest tests/test_classification.py -v`
Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add playtrace/ingest/prefetch.py playtrace/ingest/userassist.py playtrace/ingest/amcache.py playtrace/parsers/prefetch.py playtrace/parsers/userassist.py playtrace/parsers/amcache.py tests/test_classification.py tests/fixtures/prefetch/sample.json tests/fixtures/userassist/sample.json tests/fixtures/amcache/sample.json
git commit -m "feat: ingest prefetch userassist and amcache evidence"
```

### Task 5: Restore Title Resolution, Manual Mapping, and Classification Boundaries

**Files:**
- Modify: `playtrace/classify/rules.py`
- Modify: `playtrace/classify/heuristics.py`
- Modify: `playtrace/classify/resolver.py`
- Modify: `playtrace/merge/titles.py`
- Modify: `playtrace/merge/confidence.py`
- Modify: `playtrace/models/title.py`
- Modify: `playtrace/models/mapping.py`
- Modify: `playtrace/services/mapper.py`
- Create: `tests/test_title_resolution.py`

- [x] **Step 1: Write failing title-resolution tests**

```python
def test_launcher_child_rule_prefers_longest_lived_game_process() -> None: ...
def test_manual_mapping_overrides_metadata_fallback() -> None: ...
def test_helper_process_is_suppressed_from_primary_title() -> None: ...
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_title_resolution.py -v`
Expected: FAIL because title aggregation currently groups by product name or filename only.

- [x] **Step 3: Expand classification outputs**

Add support for:
- primary bucket: `game`, `launcher`, `helper`, `runtime`, `overlay`, `system`, `unknown`
- subtype: `anti_cheat`, `crash_reporter`, `updater`, `browser_wrapper`, `installer`

- [x] **Step 4: Implement relationship-aware title resolution**

Rules:
- prefer the longest-lived launcher child
- boost repeated child processes with focus time or prefetch support
- suppress helpers and runtimes
- let manual mappings override heuristic titles

```python
def resolve_title(executable: ExecutableIdentity, related_sessions: list[SessionRecord]) -> ResolvedTitle: ...
```

- [x] **Step 5: Separate metric confidence from evidence strength**

Ensure `runtime_confidence`, `launches_confidence`, `classification_confidence`, and `title_confidence` are computed independently instead of reusing a single enum everywhere.

- [x] **Step 6: Update `MapperService` to persist durable overrides**

Manual mappings must target normalized executable identities and survive rebuilds from stored artifacts.

- [x] **Step 7: Run title-resolution tests**

Run: `uv run pytest tests/test_title_resolution.py tests/test_classification.py -v`
Expected: PASS.

- [x] **Step 8: Commit**

```bash
git add playtrace/classify/rules.py playtrace/classify/heuristics.py playtrace/classify/resolver.py playtrace/merge/titles.py playtrace/merge/confidence.py playtrace/models/title.py playtrace/models/mapping.py playtrace/services/mapper.py tests/test_title_resolution.py tests/test_classification.py
git commit -m "feat: restore title resolution and mapping logic"
```

### Task 6: Build Provenance-Aware `report`, `inspect`, and `sources` Commands

**Files:**
- Create: `playtrace/cli/cmd_sources.py`
- Create: `playtrace/services/sources.py`
- Create: `playtrace/render/source_views.py`
- Modify: `playtrace/cli/app.py`
- Modify: `playtrace/cli/common.py`
- Modify: `playtrace/services/reporter.py`
- Modify: `playtrace/services/inspector.py`
- Modify: `playtrace/render/report_views.py`
- Modify: `playtrace/render/tables.py`
- Modify: `playtrace/render/cards.py`
- Modify: `playtrace/render/timeline.py`
- Modify: `tests/test_report_render.py`
- Create: `tests/test_sources_command.py`
- Create: `tests/test_inspect_view.py`

- [x] **Step 1: Write failing output tests**

```python
def test_report_does_not_seed_demo_data(tmp_path: Path) -> None: ...
def test_sources_view_lists_source_specific_evidence() -> None: ...
def test_inspect_view_shows_confidence_and_parent_chain() -> None: ...
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_render.py tests/test_sources_command.py tests/test_inspect_view.py -v`
Expected: FAIL because `report` still seeds demo data and there is no `sources` command yet.

- [x] **Step 3: Remove demo-data seeding from `ReporterService`**

Change `render_default()` to query persisted aggregates only. If the database is empty, render a clear guidance state instead of synthetic rows.

- [x] **Step 4: Add the `sources` command and service**

Command shape:

```python
@app.command("sources")
def sources(
    target: str = typer.Argument(..., help="Title, executable path, or internal ID."),
    db: DatabaseOption = Path("playtrace.db"),
) -> None: ...
```

- [x] **Step 5: Make `inspect` explain provenance**

`InspectorService` and `render/source_views.py` should show:
- exact vs inferred metrics
- evidence source counts
- parent-child launcher chain
- mapping source
- confidence reasoning

- [x] **Step 6: Run the reporting and provenance tests**

Run: `uv run pytest tests/test_report_render.py tests/test_sources_command.py tests/test_inspect_view.py -v`
Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add playtrace/cli/cmd_sources.py playtrace/services/sources.py playtrace/render/source_views.py playtrace/cli/app.py playtrace/cli/common.py playtrace/services/reporter.py playtrace/services/inspector.py playtrace/render/report_views.py playtrace/render/tables.py playtrace/render/cards.py playtrace/render/timeline.py tests/test_report_render.py tests/test_sources_command.py tests/test_inspect_view.py
git commit -m "feat: add provenance-aware reporting and sources command"
```

### Task 7: Add SRUM, BAM, and Coverage-Focused `doctor`

**Files:**
- Create: `playtrace/ingest/srum.py`
- Create: `playtrace/ingest/bam.py`
- Modify: `playtrace/parsers/srum.py`
- Modify: `playtrace/parsers/bam.py`
- Modify: `playtrace/services/doctor.py`
- Create: `tests/fixtures/srum/sample.csv`
- Create: `tests/fixtures/bam/sample.json`
- Create: `tests/test_doctor.py`

- [x] **Step 1: Write failing SRUM/BAM and doctor tests**

```python
def test_srum_parser_emits_activity_windows() -> None: ...
def test_bam_parser_emits_weak_execution_evidence() -> None: ...
def test_doctor_reports_exact_runtime_coverage_expectations() -> None: ...
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_doctor.py -v`
Expected: FAIL until the parsers and doctor service are implemented.

- [x] **Step 3: Add SRUM and BAM collectors and parsers**

Keep them downstream of the same raw-artifact and evidence pipeline. SRUM should emit activity windows and optional network usage; BAM should emit weak execution hints only.

- [x] **Step 4: Upgrade `DoctorService` from environment check to coverage explainer**

Doctor output should answer:
- are security logs available for exact runtime
- are supporting sources available
- what confidence tiers the user should expect
- what evidence is missing

- [x] **Step 5: Run the doctor test suite**

Run: `uv run pytest tests/test_doctor.py -v`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add playtrace/ingest/srum.py playtrace/ingest/bam.py playtrace/parsers/srum.py playtrace/parsers/bam.py playtrace/services/doctor.py tests/test_doctor.py tests/fixtures/srum/sample.csv tests/fixtures/bam/sample.json
git commit -m "feat: add srum bam and coverage-focused doctor output"
```

### Task 8: End-to-End Rebuildability and Final Verification

**Files:**
- Modify: `playtrace/store/db.py`
- Modify: `playtrace/store/repositories.py`
- Modify: `playtrace/services/scanner.py`
- Modify: `README.md`
- Test: `tests/test_store_schema.py`
- Test: `tests/test_security_log_pipeline.py`
- Test: `tests/test_identity.py`
- Test: `tests/test_merge_sessions.py`
- Test: `tests/test_classification.py`
- Test: `tests/test_title_resolution.py`
- Test: `tests/test_report_render.py`
- Test: `tests/test_sources_command.py`
- Test: `tests/test_inspect_view.py`
- Test: `tests/test_doctor.py`

- [x] **Step 1: Add one rebuildability test**

```python
def test_titles_can_be_rebuilt_from_artifacts_and_mappings(tmp_path: Path) -> None:
    ...
```

- [x] **Step 2: Run that test to verify it fails**

Run: `uv run pytest tests/test_store_schema.py::test_titles_can_be_rebuilt_from_artifacts_and_mappings -v`
Expected: FAIL until rebuild logic exists.

- [x] **Step 3: Implement rebuild-only aggregate flows**

Ensure the scanner and storage layer can:
- clear derived tables safely
- rebuild executables, sessions, and titles from persisted artifacts plus mappings
- avoid relying on demo data or one-shot in-memory state

- [x] **Step 4: Update `README.md` with the v2 data model and commands**

Document:
- raw evidence persistence
- exact vs inferred metrics
- `sources` and `inspect`
- fixture-driven tests

- [x] **Step 5: Run the full test suite**

Run: `uv run pytest`
Expected: PASS with non-zero collected tests.

- [x] **Step 6: Smoke-test the CLI**

Run:
- `uv run python -m playtrace --help`
- `uv run python -m playtrace sources --help`
- `uv run python -m playtrace doctor --help`

Expected: all commands exit 0 and list the v2 command surface.

- [x] **Step 7: Commit**

```bash
git add playtrace/store/db.py playtrace/store/repositories.py playtrace/services/scanner.py README.md tests
git commit -m "feat: finalize rebuildable playtrace v2 pipeline"
```

## Execution Notes

- Do not implement UI polish ahead of provenance and exact-session flow.
- Do not merge titles by filename alone.
- Do not let weaker evidence overwrite exact Security Log sessions.
- Keep each task independently reviewable and runnable.
- If a task reveals missing architecture, update `docs/spec-v2-diff.md` before continuing implementation.
